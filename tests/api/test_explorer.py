from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from html import unescape
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from psycopg_pool import PoolClosed

from public_intelligence.api.app import create_app
from public_intelligence.domain.procurement import (
    Award,
    Contract,
    Money,
    OrganizationRef,
    ProcurementProcedure,
    ProcurementRecord,
    SourceReference,
)
from public_intelligence.persistence import (
    PostgresDatabase,
    ProcurementRepository,
    RawEvidenceInput,
    RawEvidenceRepository,
)


@pytest.fixture
async def client(
    test_database_url: str,
    database: PostgresDatabase,
) -> AsyncIterator[AsyncClient]:
    del database  # Keep the disposable database initialized and isolated for this test.
    application = create_app(test_database_url)
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
        ) as test_client:
            yield test_client


@pytest.fixture
def procurement_repository(database: PostgresDatabase) -> ProcurementRepository:
    return ProcurementRepository(database)


@pytest.mark.anyio
async def test_database_url_is_resolved_at_lifespan_and_pool_is_closed(
    monkeypatch: pytest.MonkeyPatch,
    test_database_url: str,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    application = create_app()
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    async with application.router.lifespan_context(application):
        managed_database = application.state.database
        first_queries = application.state.procurement_queries
        assert application.state.procurement_queries is first_queries

    with pytest.raises(PoolClosed):
        async with managed_database.connection():
            pass


@pytest.mark.anyio
async def test_health_contract_and_package_static_asset(client: AsyncClient) -> None:
    health = await client.get("/health")
    stylesheet = await client.get("/static/styles.css")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert "font-family" in stylesheet.text


@pytest.mark.anyio
async def test_empty_database_and_no_matches_have_distinct_messages(
    client: AsyncClient,
    procurement_repository: ProcurementRepository,
) -> None:
    empty = await client.get("/")
    await procurement_repository.save(_record(external_id="one"))
    no_matches = await client.get("/", params={"buyer": "absent"})

    assert empty.status_code == 200
    assert "No normalized procurements are available yet" in empty.text
    assert "0 total · showing 0–0" in empty.text
    assert no_matches.status_code == 200
    assert "No procurements match these filters" in no_matches.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "parameters",
    [
        {"buyer": "   "},
        {"supplier": "\t"},
        {"status": " "},
        {"currency": "\n"},
        {"min_value": "invalid"},
        {"min_value": "NaN", "currency": "USD"},
        {"min_value": "1"},
        {"min_value": "2", "max_value": "1", "currency": "USD"},
        {"limit": "0"},
        {"limit": "201"},
        {"limit": "invalid"},
        {"offset": "-1"},
    ],
)
async def test_invalid_search_parameters_render_html_422(
    client: AsyncClient,
    parameters: dict[str, str],
) -> None:
    response = await client.get("/", params=parameters)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert "Invalid search:" in response.text


@pytest.mark.anyio
async def test_search_filters_render_minimal_source_independent_projection(
    client: AsyncClient,
    procurement_repository: ProcurementRepository,
) -> None:
    precise = Decimal("12345678901234567890.123400")
    await procurement_repository.save(
        _record(
            source="example_source",
            external_id="example & one",
            buyer="Public Water Buyer",
            supplier="Acme Supply",
            status="active",
            amount=precise,
            currency="USD",
        )
    )
    await procurement_repository.save(
        _record(
            source="sercop",
            external_id="other",
            buyer="Other Buyer",
            supplier="Other Supplier",
            status="active",
            amount=Decimal("10"),
            currency="USD",
        )
    )

    response = await client.get(
        "/",
        params={
            "buyer": "water",
            "supplier": "ACME",
            "status": "active",
            "currency": "USD",
            "min_value": str(precise),
            "max_value": str(precise),
        },
    )

    assert response.status_code == 200
    assert "1 total · showing 1–1" in response.text
    assert "example_source" in response.text
    assert "example &amp; one" in response.text
    assert "Public Water Buyer" in response.text
    assert "Example procedure" in response.text
    assert f"{precise} USD" in response.text
    assert "+00:00" not in response.text
    assert "Z</time>" in response.text
    assert "sercop" not in response.text


@pytest.mark.anyio
async def test_pagination_preserves_filters_and_handles_out_of_range_page(
    client: AsyncClient,
    procurement_repository: ProcurementRepository,
) -> None:
    for external_id in ("c", "b", "a"):
        await procurement_repository.save(
            _record(external_id=external_id, buyer="Buyer & Co")
        )

    middle = await client.get(
        "/",
        params={"buyer": "Buyer & Co", "limit": "1", "offset": "1"},
    )
    beyond = await client.get(
        "/",
        params={"buyer": "Buyer & Co", "limit": "1", "offset": "9"},
    )

    assert middle.status_code == 200
    assert "3 total · showing 2–2" in middle.text
    assert "buyer=Buyer+%26+Co" in unescape(middle.text)
    assert "offset=0" in unescape(middle.text)
    assert "offset=2" in unescape(middle.text)
    assert beyond.status_code == 200
    assert "3 total · showing 0–0" in beyond.text
    assert "This result page is empty" in beyond.text
    assert "offset=8" in unescape(beyond.text)


@pytest.mark.anyio
async def test_detail_uses_query_identity_and_renders_full_normalized_record(
    client: AsyncClient,
    procurement_repository: ProcurementRepository,
    repository: RawEvidenceRepository,
) -> None:
    payload = b'{"fixture":true}'
    evidence = await repository.save(
        RawEvidenceInput(
            source="example_source",
            mechanism="fixture",
            source_key="detail",
            endpoint="/fixture/detail",
            parameters={},
            retrieved_at=datetime(2026, 8, 28, tzinfo=UTC),
            http_status=200,
            content_type="application/json",
            payload_sha256=sha256(payload).hexdigest(),
            payload_byte_size=len(payload),
            payload=payload,
        )
    )
    await procurement_repository.save(
        _record(
            external_id="identity /?&",
            evidence_id=evidence.id,
            amount=Decimal("0"),
            currency=None,
            full=True,
        )
    )

    listing = await client.get("/")
    href = _detail_href(listing.text, "identity /?&")
    identity = parse_qs(urlsplit(href).query)
    detail = await client.get(href)

    assert identity == {
        "source": ["example_source"],
        "external_id": ["identity /?&"],
    }
    assert detail.status_code == 200
    assert str(evidence.id) in detail.text
    assert "0 (currency not supplied)" in detail.text
    assert "Factual description" in detail.text
    assert "Procurement Supplier" in detail.text
    assert "Award Supplier" in detail.text
    assert "award-1" in detail.text
    assert "contract-1" in detail.text
    assert "2026-08-21T12:00:00Z" in detail.text
    assert payload.decode() not in detail.text


@pytest.mark.anyio
async def test_detail_distinguishes_absent_and_empty_collections(
    client: AsyncClient,
    procurement_repository: ProcurementRepository,
) -> None:
    await procurement_repository.save(_record(external_id="absent"))
    await procurement_repository.save(
        _record(external_id="empty", suppliers=(), awards=(), contracts=())
    )

    absent = await client.get(
        "/procurements/detail",
        params={"source": "example_source", "external_id": "absent"},
    )
    empty = await client.get(
        "/procurements/detail",
        params={"source": "example_source", "external_id": "empty"},
    )

    assert absent.status_code == 200
    assert absent.text.count("Not supplied") >= 4
    assert "Supplied as an empty collection" not in absent.text
    assert empty.status_code == 200
    assert empty.text.count("Supplied as an empty collection") == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("parameters", "status_code"),
    [
        ({}, 422),
        ({"source": " ", "external_id": "id"}, 422),
        ({"source": "example_source", "external_id": "unknown"}, 404),
    ],
)
async def test_detail_validation_and_unknown_identity(
    client: AsyncClient,
    parameters: dict[str, str],
    status_code: int,
) -> None:
    response = await client.get("/procurements/detail", params=parameters)

    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("text/html")


def _record(
    *,
    external_id: str,
    source: str = "example_source",
    evidence_id: UUID | None = None,
    buyer: str | None = None,
    supplier: str | None = None,
    status: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    full: bool = False,
    suppliers: tuple[OrganizationRef, ...] | None = None,
    awards: tuple[Award, ...] | None = None,
    contracts: tuple[Contract, ...] | None = None,
) -> ProcurementRecord:
    if supplier is not None:
        suppliers = (OrganizationRef(external_id="supplier-1", name=supplier),)
    if full:
        suppliers = (
            OrganizationRef(external_id="supplier-1", name="Procurement Supplier"),
        )
        awards = (
            Award(
                external_id="award-1",
                status="active",
                date=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
                value=Money(Decimal("5.50"), "USD"),
                suppliers=(OrganizationRef(None, "Award Supplier"),),
            ),
        )
        contracts = (
            Contract(
                external_id="contract-1",
                award_external_id="award-1",
                status=None,
                date_signed=None,
                value=None,
            ),
        )
    procedure = ProcurementProcedure(
        external_id=f"procedure-{external_id}",
        title="Example procedure",
        description="Factual description" if full else None,
        status=status,
        method="open" if full else None,
        method_details=None,
        category="services" if full else None,
        value=Money(amount, currency) if amount is not None else None,
    )
    return ProcurementRecord(
        source_reference=SourceReference(
            source=source,
            external_id=external_id,
            evidence_id=evidence_id,
        ),
        buyer=OrganizationRef(None, buyer) if buyer is not None else None,
        suppliers=suppliers,
        procedure=procedure,
        awards=awards,
        contracts=contracts,
    )


def _detail_href(document: str, label: str) -> str:
    escaped_label = label.replace("&", "&amp;")
    marker = f">{escaped_label}</a>"
    before, separator, _ = document.partition(marker)
    assert separator
    href_start = before.rfind('href="') + len('href="')
    return unescape(before[href_start:].removesuffix('"'))
