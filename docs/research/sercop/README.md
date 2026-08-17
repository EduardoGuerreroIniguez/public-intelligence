# SERCOP source research

**Research date:** 2026-08-17  
**Spec:** [SPEC-002](../../specs/SPEC-002-sercop-data-source-research.md)

## Executive summary

- **Verified — documented:** SERCOP publishes procurement data through a
  keyword-search API, an OCID lookup API, and bulk downloads in JSON, CSV, and
  XLSX. The official pages describe coverage beginning in 2015.
- **Verified — observed:** Unauthenticated search and OCID requests succeeded
  for both 2015 and 2026. Responses exposed `X-RateLimit-Limit: 60`, but the
  time window and enforcement policy are not documented.
- **Verified — observed:** Contrary to the official API example, the OCID
  endpoint returned an OCDS release package with a top-level `releases` array,
  not a record package with `records`, `compiledRelease`, or
  `versionedRelease`.
- **Verified — observed:** Each of five inspected OCIDs returned exactly one
  release. Three release IDs ended in `-compiled`, and releases combined
  multiple lifecycle tags. The endpoint did not expose prior states.
- **Recommendation:** Use the search API only for discovery and the OCID API
  for targeted source snapshots. Investigate bulk JSON as the historical
  ingestion input; preserve the original source artifacts and provenance.
- **Recommendation:** Do not derive Public Intelligence events from the
  currently observed single-release snapshots. The inspected publication does
  not establish reliable change history.

## Research conclusion

SERCOP is viable as a targeted public-data source, and its official bulk
publication is a plausible basis for later historical ingestion. The first
connector should remain small and source-specific: keyword discovery, OCID
lookup, raw response preservation, and explicit handling of the observed
release-package shape.

The source is not a safe basis for an internal procurement domain model yet.
Observed nullability, composite organization identifiers, lifecycle/status
inconsistencies, and the absence of exposed version history must remain source
concerns until broader evidence exists.

## Evidence classification

- **Verified — documented:** stated by an official SERCOP or OCDS source.
- **Verified — observed:** demonstrated by a request or inspected artifact.
- **Observed:** true of a named sample, without dataset-wide generalization.
- **Suspected:** plausible but requiring broader evidence.
- **Unknown:** not established by official documentation or this sample.
- **Recommendation:** an engineering conclusion based on cited evidence.

## Detailed artifacts

- [Access mechanisms](access.md)
- [Observed data model](data-model.md)
- [Data quality and uncertainty](data-quality.md)
- [Ingestion recommendation](ingestion-recommendation.md)
- [Sample provenance](samples/README.md)

## Key remaining unknowns

- Whether SERCOP exposes immutable historical releases through another public
  mechanism.
- The precise rate-limit window and operational policy.
- Whether composite `EC-RUC-<13 digits>-<suffix>` identifiers are stable across
  all procurement types and years.
- How representative the sampled nulls and status inconsistencies are.
- Whether bulk partitions overlap or are ever republished with changed
  contents.
- Whether document metadata is populated in procurement types not sampled.

## Completion status

All applicable SPEC-002 research artifacts and acceptance criteria were
completed. No external-service criterion remained blocked on 2026-08-17.
