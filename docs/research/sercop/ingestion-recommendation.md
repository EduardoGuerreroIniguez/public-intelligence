# SERCOP ingestion recommendation

This is a research conclusion for future specifications. It does not implement
a connector, persistence, domain entities, or events.

## Targeted lookup

**Recommendation:** SPEC-003 should implement only a SERCOP-specific connector
for:

1. keyword discovery through `search_ocds`; and
2. exact snapshot retrieval through `record?ocid=...`.

The connector should use documented parameters even though missing `search`
was accepted during research. It should model search summaries separately from
the live release-package response, accept nullable source fields, and translate
HTML 404 responses into an internal source-access error.

The connector boundary may fetch, validate source envelopes, handle
pagination, expose source DTOs, and preserve raw responses. It must not create
domain events, resolve entities, score opportunities, or introduce generic
connector frameworks.

## Historical ingestion

**Recommendation:** A later, separate historical-ingestion spec should use
bulk JSON partitioned by year, month, and procurement type.

Reasons:

- The official UI supports bounded partitions and exposes counts.
- JSON retained nested parties, items, extensions, and source structures.
- CSV/XLSX flattened data into eight tables and did not represent all observed
  nested structures equivalently.
- Bulk access avoids paginating keyword-search results for history.

Before production ingestion, verify partition overlap, republishing behavior,
file checksums, failure recovery, and responsible request cadence. Do not add
this behavior to SPEC-003 unless that spec explicitly chooses it.

## Raw-data preservation

Preserve the source before normalization:

- For API access: exact response body plus request metadata.
- For bulk access: original downloaded ZIP/XLSX artifact, checksum, source
  filename, filters, `Last-Modified`, and retrieval metadata.
- Preserve package metadata, declared extensions, and unknown fields.
- Treat source raw data as evidence, not as the internal domain model.

The future raw-storage unit can combine API snapshots and original bulk
artifacts. The persistence technology remains undecided.

## Identifiers to retain

At minimum retain:

- `ocid` as the external contracting-process identifier.
- Release `id`, `date`, and `tag` as source snapshot metadata.
- Tender, award, and contract IDs, including `awardID` links.
- Complete party IDs and `identifier` blocks.
- Any separately validated candidate RUC without replacing the complete source
  identifier.
- Related-process identifiers and relationships.

Do not use numeric search `id` as the process identity.

## Minimum provenance

Future ingestion should record:

- Source key (`sercop`).
- Access mechanism and endpoint.
- Exact request parameters, OCID, or bulk partition filters.
- Retrieval timestamp in UTC.
- HTTP status, content type, and relevant source headers.
- Payload/artifact SHA-256 and byte size.
- Publisher, package URI, OCDS version, publication date, license, publication
  policy, and declared extensions when present.
- Completeness/truncation and any transformation applied after capture.

## Historical-event feasibility

**Verified — observed:** Five OCIDs exposed one multi-tag release each and no
versioned or compiled release object. This is insufficient to reconstruct
source changes reliably.

**Recommendation:** SPEC-003 must not emit Public Intelligence events from tags
alone. A later spec may investigate change detection across independently
captured snapshots or a source mechanism that exposes immutable releases, but
must distinguish source facts, observed changes, and derived interpretations.

## Proposed bounded scope for SPEC-003

- SERCOP-specific HTTP client/connector module.
- Keyword-search request and pagination DTOs.
- OCID snapshot request and release-package DTOs matching captured fixtures.
- Source-specific errors for unavailable, not-found, malformed, and unexpected
  content-type responses.
- Raw body and provenance handoff at the application boundary.
- Contract tests using SPEC-002 fixtures; live tests manual/explicit only.

Explicitly exclude bulk ingestion, persistence, domain procurement entities,
entity resolution, internal events, signals, scheduling, retries as a generic
framework, and API/UI exposure.

## Unresolved risks

- Source response shapes have diverged from documentation.
- Rate-limit policy is incomplete.
- Composite organization identifiers require source-specific validation.
- Snapshot history and republishing semantics are unknown.
- Extension URLs and fields may evolve independently.
- Data quality remains dependent on originating entities and SERCOP source
  transformations.
