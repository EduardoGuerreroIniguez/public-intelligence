# SERCOP data quality findings

Findings are limited to official documentation and the bounded samples
inspected on 2026-08-17. They are not dataset-wide claims.

## Observed

1. **API documentation and live shape differ.** The OCID documentation shows a
   record package, while five live responses were release packages. Search
   field names also differed from the documentation example.
2. **Single snapshot-like release.** Every inspected OCID contained one release
   combining multiple lifecycle tags. Three release IDs ended in `-compiled`.
3. **No exposed version history.** No `records`, `compiledRelease`, or
   `versionedRelease` appeared.
4. **Lifecycle field combination.** One sample had tender status `active`,
   contract status `terminated`, and an `implementation` release tag without a
   contract implementation object. The inspected official sources did not
   establish a cross-field invariant that would classify this combination as
   inconsistent.
5. **Nullable award status.** Three current-year awards had no status while two
   catalog awards used `active`.
6. **Buyer reference mismatch.** In both catalog samples, `buyer.id` omitted a
   suffix present in `parties[].id`; `tender.procuringEntity.id` matched.
7. **Composite organization identifiers.** `identifier.id` included the
   `EC-RUC` prefix and a source suffix in addition to the apparent 13-digit RUC.
8. **Sparse values and periods.** Tender, contract, signing-date, period, and
   category fields were absent or null in some inspected records. In one
   Subasta Inversa record, `tender.value` was absent while downstream values
   were populated. The sample does not establish that sparsity is caused by or
   systematically varies with procurement type.
9. **Different date concepts.** A 2015 release was packaged in 2021, and release
   IDs can contain a `Z` timestamp distinct from the release's `-05:00` date.
10. **Search nulls.** Three of ten rows in the 2026 `agua` page had null method,
    internal type, amount, title, description, supplier, and budget fields.
11. **No documents in the sample.** Tender, award, and contract documents were
    absent across five records; this does not establish global absence.
12. **Tabular bulk formats are selective.** The inspected CSV/XLSX partition
    used eight flattened tables/sheets and did not preserve every nested JSON
    structure as a corresponding table.
13. **Validation behavior differs from documentation.** Omitting required
    `search` returned 200 and unfiltered summaries. An unknown OCID returned an
    HTML 404 rather than JSON.

## Suspected

- Releases with `-compiled` IDs appear to be synthesized current-state
  snapshots, but naming alone cannot establish the exact generation process.
- The 13-digit segment inside composite `EC-RUC` values is likely useful for
  organization matching, but stability across all source systems is unproven.
- Bulk JSON appears more source-faithful than CSV/XLSX, though only one
  three-process partition was compared.
- Current-year data may change after nightly processing or later corrections.

## Unknown

- Whether immutable historical releases are publicly retrievable elsewhere.
- Rate-limit window, reset behavior, and official client guidance.
- Dataset-wide frequency of nulls, reference mismatches, duplicate-looking
  records, name variations, encoding issues, and unexpected data types.
- Whether bulk partitions are disjoint and whether published files are revised.
- Document availability across other procurement types.
- Coverage and stability of every declared extension.
- Whether `correctedValue` and `enteredValue` are consistently populated.
- Whether lifecycle fields are expected to satisfy cross-field status or tag
  invariants beyond their individual OCDS codelists.
- Whether field presence systematically varies by procurement type.

## Sample caveats

- Five OCIDs and one three-process bulk partition are deliberately small.
- The sample covers 2015 and 2026 and four procurement descriptions, but is not
  statistically representative.
- Current-year records can have incomplete or evolving lifecycle states.
- Search terms influence which procurement types and organizations appear.
- Personal-data-heavy samples used for structural observations were not
  committed. Raw committed samples were selected for legal-entity parties when
  practical and were not semantically cleaned.

## Implications for a future connector

- Validate actual source envelopes and nullable fields with captured fixtures.
- Preserve unknown and extension fields in raw source data.
- Treat identifiers as opaque until source-specific parsing is explicitly
  specified and tested.
- Translate HTML 404s and payload-shape failures into connector-level errors.
- Do not equate multi-tag snapshots with independent business events.
