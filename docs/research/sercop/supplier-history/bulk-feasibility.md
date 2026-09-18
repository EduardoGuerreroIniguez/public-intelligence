# Bulk feasibility for ELECTROLEG

**Research date:** 2026-09-18  
**Candidate window:** 2025-01 through 2026-09

## Current official public mechanism

The official
[SERCOP bulk-download page](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos)
was retrieved successfully on 2026-09-18.

**Verified — official public page:** it offers procurement downloads by:

```text
year + month + procurement type
```

in JSON, CSV, and XLSX. The public page constructs downloads using:

```text
/download?type=<format>&year=<year>&month=<month>&method=<method>
```

and displays counts using the previously established public mechanism:

```text
/get-totals?year=<year>&month=<month>&method=<method>
```

The retrieved page body was 15,553 bytes with SHA-256
`c2a5e03dd8c635d8f22ff18d9649ebc2da89cfe8315f3b5a5188cd5ad8118e35`.

No hidden/internal endpoint was inspected. The page itself publishes the
coverage dates, method choices, download URL, and count URL.

## Partition discovery

**Verified — official public page, 2026-09-18:**

- advertised coverage is 2015-01 through 2026-09;
- 2026 exposes months January through September;
- the page contains 27 named procurement types;
- it also contains `Todos los tipos de contratación` with value `all`;
- month value `0` is presented as `todos`.

The candidate ELECTROLEG range has 21 months:

```text
2025: 12 months
2026:  9 months
total: 21 months
```

Two bounded partition strategies are therefore visible in the official UI:

| Strategy | Candidate requests/artifacts | Current certainty |
| --- | ---: | --- |
| Every specific type for every month | 27 × 21 = 567 | Dimension count is Verified; non-empty count is Unknown |
| One `method=all` artifact per month | 21 | Option is Verified; artifact size, exact composition, overlap, and parser compatibility are Unknown |

The `all` option is the smallest candidate for the commercial experiment, but
must be validated with one bounded artifact before adoption. It must not be
assumed equivalent to a union of all 27 specific types until observed.

## Discovery work not performed

The plan called for a small number of `/get-totals` requests to estimate the
range. They were not executed because the first targeted API probe returned
HTTP 429 and the research stop rule applies to further SERCOP requests.

Consequently, these remain **Unknown** for the target window:

- monthly all-type record counts;
- which specific type/month combinations are empty;
- current artifact byte sizes;
- largest partition;
- whether September 2026 is complete;
- whether artifacts are revised after publication;
- whether specific-type artifacts overlap with `all` beyond the obvious
  alternative download views.

## Existing evidence about bulk shape

**Observed — SPEC-002, 2026-08-17:** a small 2026-07 partition for
`Obra artística, científica o literaria` reported three procedures. Its JSON
download was a 3,119-byte ZIP with one 16,640-byte JSON member containing an
array of three release packages.

**Observed:** JSON retained nested parties, items, and extension structures
that the inspected CSV/XLSX forms flattened selectively.

This proves bounded compatibility for one small specific-type partition only.
It does not prove that large or `all` artifacts fit comfortably in memory.

## Existing component reuse

| Component | Reusable capability | Constraint for a future corpus |
| --- | --- | --- |
| `SercopBulkPartition` | Exact year/month/type request | One explicit partition only; `all` is syntactically accepted but untested |
| `SercopBulkClient.download()` | Official JSON ZIP request with provenance | Buffers the complete HTTP body; no retries |
| `parse_bulk_artifact()` | One ZIP member containing a non-empty package array | Entire ZIP/member parsed in memory; observed shape only |
| `ingest_partition()` | Artifact and canonical package evidence persistence | One atomic partition; no checkpoint/resume |
| `process_partition()` | Evidence → mapper → normalized persistence | One partition; duplicate identities inside a run fail |
| `map_procurement_package()` | Award suppliers and factual procurement mapping | One release per package; item/CPC and party identifier detail not normalized |
| `ProcurementRepository` | Snapshot replacement by source/external ID | Later observations replace the normalized snapshot |
| `ProcurementQueries` | Name search over aggregated award suppliers | Does not expose award-level matching or stable supplier identity |

No redesign is required to prove one additional partition. A multi-partition
corpus workflow would need an accepted bounded orchestration spec, an explicit
manifest, and clear partial-failure/resume semantics. SPEC-011 does not build
that workflow.

## Feasibility conclusion

- **Verified:** official bulk coverage includes the candidate months and
  provides JSON downloads.
- **Observed:** the existing implementation processes one small official JSON
  partition end to end.
- **Unknown:** total volume and buffering feasibility for monthly all-type
  artifacts.
- **Unknown:** whether 21 `all` artifacts are the correct minimal complete
  partition set.

Bulk is the only reviewed official mechanism that can define a historical
acquisition universe without product keywords. It is feasible enough to
justify a bounded next-spec proof, but not yet enough to authorize an automatic
21-month backfill.

The next implementation should first validate one representative
`method=all` month, record its count/size/shape, and require a human-reviewed
explicit partition manifest before expanding the corpus.

