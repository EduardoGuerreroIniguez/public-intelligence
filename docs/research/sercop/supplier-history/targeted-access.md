# Targeted supplier access

**Research date:** 2026-09-18

## Official documentation rechecked

The current official
[SERCOP API documentation](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/api)
was retrieved successfully on 2026-09-18.

**Verified — official documentation:** the page describes two targeted
operations:

1. keyword search through `GET /api/search_ocds`;
2. exact process lookup through `GET /api/record?ocid=...`.

The documented search parameters are:

| Parameter | Required | Documented semantics |
| --- | --- | --- |
| `year` | Yes | Integer from 2015 through the current year |
| `search` | Yes | Keyword containing at least three characters |
| `page` | No | Positive integer |
| `buyer` | No | Keyword for locating a purchasing institution; at least three characters |
| `supplier` | No | Keyword for locating a particular supplier; at least three characters |

**Verified — official documentation:** the page does not define whether the
supplier keyword uses exact equality, substring matching, normalization, RUC,
party ID, award-supplier data, or another index. It does not document a
supplier-only endpoint or neutral/wildcard search value.

The retrieved documentation body was 15,696 bytes with SHA-256
`1a88008c536806c715ddc2554acda2b8be9d78edbda56d3cebc317cbaeb603cf`.
It is not committed because its relevant contract is cited and summarized here.

## Omitted and empty `search`

**Verified — official documentation:** `search` is mandatory and must contain
at least three characters.

No omitted-search or empty-search request was made. The documentation is
sufficient to conclude that neither is an officially supported supplier-only
query. Existing SPEC-002 evidence that an omitted `search` once returned data
remains an Observed discrepancy, not a production contract. No wildcard or
validation-bypass probe was attempted.

## Prior bounded observations

The following observations were recorded in SPEC-011 before this execution:

| Request | Observed result | Interpretation limit |
| --- | --- | --- |
| 2018 + `accesorios` + `ELECTROLEG` | One result; supplier `ELECTROLEG S.A.`; OCID `ocds-5wno2w-SIE-EEASA-002-2018-3233` | Supports partial-name matching for one case only |
| 2025 + `interruptor` + `ELECTROLEG` | Zero | Does not prove no 2025 awards |
| 2026 + `medidor` + `ELECTROLEG` | Zero | Does not prove no 2026 awards |
| 2026 + `energia` + `ELECTROLEG` | Zero | Does not prove no 2026 awards |
| 2025 + `interruptor`, no supplier | Seven | Confirms the keyword itself had results |
| 2026 + `medidor`, no supplier | 137 across 14 pages | Confirms the keyword itself had results |

These are **Observed**, not Verified source guarantees.

## Planned control matrix and actual execution

The planned sequence held year and keyword constant while varying only the
supplier representation.

| ID | Request | Outcome |
| --- | --- | --- |
| S1 | 2018 + `accesorios`, supplier omitted | **Performed:** HTTP 429; no JSON search result |
| S2 | Same + `ELECTROLEG` | **Skipped:** execution stopped after S1 returned 429 |
| S3 | Same + `ELECTROLEG S.A.` | **Skipped:** execution stopped after 429 |
| S4 | Same + observed 13-digit RUC | **Skipped:** no record identity could be inspected after 429 |
| S5 | Same + complete source organization ID | **Skipped:** no record identity could be inspected after 429 |
| S6 | Same + deliberately nonexistent supplier | **Skipped:** execution stopped after 429 |
| S7–S10 | Current-period positive/negative keyword controls | **Skipped:** prior observations already exist and execution stopped after 429 |
| S11 | Supplier with omitted `search` | **Skipped:** official documentation is sufficient; unsupported contract |
| S12 | Supplier with empty `search` | **Skipped:** official documentation is sufficient; unsupported contract |

No attempt was made to reproduce the historical 429, discover its threshold,
or resume after `Retry-After`.

## Current access-restriction evidence

The only API probe in this execution was sent at approximately
2026-09-18T16:00:54Z:

```text
GET /PLATAFORMA/api/search_ocds
    ?year=2018
    &search=accesorios
    &page=1
```

It returned:

```text
HTTP 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
Retry-After: 28
X-RateLimit-Reset: 1789747282
Content-Type: text/html; charset=UTF-8
```

The reset value corresponds to `2026-09-18T16:01:22Z`. The 6,625-byte HTML
body had SHA-256
`175b1fdf5e258e4aa0afadb61488bdd7d25e40df8f31bf5ba215726f7d66bdc3`.
The body is not committed because it adds no durable semantic evidence.

- **Observed:** SERCOP supplied both `Retry-After` and rate-limit headers for
  this 429.
- **Observed:** prior successful API responses exposed a limit of 60.
- **Unknown:** the rate-limit window, accounting identity, whether the quota is
  shared, and the exact enforcement policy.

A future implementation should respect `Retry-After` when present, use bounded
backoff only under an accepted implementation spec, and fail explicitly after
the bounded policy. SPEC-011 implements no retries.

## Supplier matching conclusions

| Matching question | Conclusion |
| --- | --- |
| Partial `ELECTROLEG` → `ELECTROLEG S.A.` | **Observed** in the prior 2018 request |
| Exact legal name | **Unknown**; planned request was stopped |
| RUC | **Unknown** |
| Complete party/source ID | **Unknown** |
| Case/accent/punctuation normalization | **Unknown** |
| Stable behavior across procurement types | **Unknown** |
| Dataset-wide substring semantics | **Unknown** |

## Completeness conclusion

**Verified — official documentation:** targeted search requires a keyword in
addition to any supplier filter.

**Conclusion:** the targeted API is not an officially supported mechanism for
reconstructing complete supplier award history without arbitrary keyword
selection. It remains useful for bounded discovery and verification when
access is available. A zero result is scoped only to the exact year, keyword,
supplier value, and source state used by that request.

