"""Server-rendered browser explorer for normalized procurement facts."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import QueryParams

from public_intelligence.domain.procurement import Money
from public_intelligence.persistence import (
    ProcurementQueries,
    ProcurementSearch,
    ProcurementSearchPage,
)

_API_DIRECTORY = Path(__file__).resolve().parent
_TEMPLATE_DIRECTORY = _API_DIRECTORY / "templates"
_SEARCH_FIELDS = (
    "buyer",
    "supplier",
    "status",
    "currency",
    "min_value",
    "max_value",
    "limit",
    "offset",
)

router = APIRouter()
templates = Jinja2Templates(directory=_TEMPLATE_DIRECTORY)


def format_money(value: Money | None) -> str:
    """Format exact money without inference or float conversion."""
    if value is None:
        return "Not supplied"
    amount = format(value.amount, "f")
    if value.currency is None:
        return f"{amount} (currency not supplied)"
    return f"{amount} {value.currency}"


def format_datetime(value: datetime | None) -> str:
    """Format timestamps deterministically in UTC."""
    if value is None:
        return "Not supplied"
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


templates.env.filters["money"] = format_money
templates.env.filters["utc_datetime"] = format_datetime


@router.get("/", response_class=HTMLResponse, name="procurement_explorer")
async def procurement_explorer(request: Request) -> HTMLResponse:
    """Render one validated procurement search page."""
    raw_form = _raw_form_values(request.query_params)
    try:
        criteria = _parse_search(request.query_params)
    except (TypeError, ValueError) as error:
        return templates.TemplateResponse(
            request=request,
            name="explorer.html",
            context={
                "error": str(error),
                "form": raw_form,
                "page": None,
                "rows": (),
                "previous_url": None,
                "next_url": None,
                "range_start": 0,
                "range_end": 0,
                "has_filters": _has_raw_filters(raw_form),
            },
            status_code=422,
        )

    queries = _queries(request)
    page = await queries.search(criteria)
    rows = tuple(
        {
            "item": item,
            "detail_url": _detail_url(
                request,
                source=item.source,
                external_id=item.external_id,
            ),
        }
        for item in page.items
    )
    return templates.TemplateResponse(
        request=request,
        name="explorer.html",
        context={
            "error": None,
            "form": _criteria_form_values(criteria),
            "page": page,
            "rows": rows,
            "previous_url": _previous_url(request, criteria, page),
            "next_url": _next_url(request, criteria, page),
            "range_start": criteria.offset + 1 if page.items else 0,
            "range_end": criteria.offset + len(page.items) if page.items else 0,
            "has_filters": _has_filters(criteria),
        },
    )


@router.get(
    "/procurements/detail",
    response_class=HTMLResponse,
    name="procurement_detail",
)
async def procurement_detail(
    request: Request,
    source: str | None = Query(default=None),
    external_id: str | None = Query(default=None),
) -> HTMLResponse:
    """Render full normalized detail through the existing repository delegation."""
    if source is None or not source.strip():
        return _detail_error(request, "source must not be blank", status_code=422)
    if external_id is None or not external_id.strip():
        return _detail_error(request, "external_id must not be blank", status_code=422)

    stored = await _queries(request).get(source=source, external_id=external_id)
    if stored is None:
        return _detail_error(
            request,
            "Procurement not found.",
            status_code=404,
            source=source,
            external_id=external_id,
        )
    return templates.TemplateResponse(
        request=request,
        name="procurement_detail.html",
        context={"error": None, "stored": stored},
    )


def _parse_search(parameters: QueryParams) -> ProcurementSearch:
    min_value = _decimal_parameter(parameters.get("min_value"), name="min_value")
    max_value = _decimal_parameter(parameters.get("max_value"), name="max_value")
    limit = _integer_parameter(parameters.get("limit"), name="limit", default=50)
    offset = _integer_parameter(parameters.get("offset"), name="offset", default=0)
    return ProcurementSearch(
        buyer=parameters.get("buyer"),
        supplier=parameters.get("supplier"),
        status=parameters.get("status"),
        currency=parameters.get("currency"),
        min_value=min_value,
        max_value=max_value,
        limit=limit,
        offset=offset,
    )


def _decimal_parameter(value: str | None, *, name: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{name} must be a valid decimal") from error


def _integer_parameter(value: str | None, *, name: str, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


def _queries(request: Request) -> ProcurementQueries:
    return cast(ProcurementQueries, request.app.state.procurement_queries)


def _raw_form_values(parameters: QueryParams) -> dict[str, str]:
    return {name: parameters.get(name, "") for name in _SEARCH_FIELDS}


def _criteria_form_values(criteria: ProcurementSearch) -> dict[str, str]:
    return {
        "buyer": criteria.buyer or "",
        "supplier": criteria.supplier or "",
        "status": criteria.status or "",
        "currency": criteria.currency or "",
        "min_value": str(criteria.min_value) if criteria.min_value is not None else "",
        "max_value": str(criteria.max_value) if criteria.max_value is not None else "",
        "limit": str(criteria.limit),
        "offset": str(criteria.offset),
    }


def _has_raw_filters(form: dict[str, str]) -> bool:
    return any(form[name] for name in _SEARCH_FIELDS[:6])


def _has_filters(criteria: ProcurementSearch) -> bool:
    return any(
        value is not None
        for value in (
            criteria.buyer,
            criteria.supplier,
            criteria.status,
            criteria.currency,
            criteria.min_value,
            criteria.max_value,
        )
    )


def _search_url(request: Request, criteria: ProcurementSearch, *, offset: int) -> str:
    values = _criteria_form_values(criteria)
    values["offset"] = str(offset)
    parameters = {name: value for name, value in values.items() if value != ""}
    base_url = str(request.url_for("procurement_explorer"))
    return f"{base_url}?{urlencode(parameters)}"


def _previous_url(
    request: Request,
    criteria: ProcurementSearch,
    page: ProcurementSearchPage,
) -> str | None:
    if criteria.offset == 0:
        return None
    return _search_url(
        request,
        criteria,
        offset=max(0, criteria.offset - page.limit),
    )


def _next_url(
    request: Request,
    criteria: ProcurementSearch,
    page: ProcurementSearchPage,
) -> str | None:
    if criteria.offset + len(page.items) >= page.total:
        return None
    return _search_url(request, criteria, offset=criteria.offset + page.limit)


def _detail_url(request: Request, *, source: str, external_id: str) -> str:
    base_url = str(request.url_for("procurement_detail"))
    return f"{base_url}?{urlencode({'source': source, 'external_id': external_id})}"


def _detail_error(
    request: Request,
    message: str,
    *,
    status_code: int,
    source: str | None = None,
    external_id: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="procurement_detail.html",
        context={
            "error": message,
            "stored": None,
            "source": source,
            "external_id": external_id,
        },
        status_code=status_code,
    )
