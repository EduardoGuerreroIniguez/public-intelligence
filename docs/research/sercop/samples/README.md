# SERCOP research sample provenance

Samples were retrieved from the official public SERCOP platform on
2026-08-17. They are research fixtures, not normalized domain data.

## Committed samples

The source bodies had no terminal newline. Repository storage added one final
LF byte; JSON values and ordering are otherwise unchanged. Both source-body and
committed-file hashes are recorded.

| File | Retrieved (UTC) | Request | HTTP/content type | Bytes source/repo | SHA-256 source | SHA-256 repo | Complete | Modification |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `search-2015-agua-page-1.json` | 2026-08-17 19:31:16Z | `search_ocds?year=2015&search=agua&page=1` | 200, `application/json` | 5,637/5,638 | `e47195ffcddd9820c446f26e19f05e33c9d075e92c3eb27019719cf9c48d21c5` | `ed6ea5c2a5bf290e8ae9a363bc6a8f8ebcb259b768d7750ea0f27f4c23f06cac` | Yes; one API page | Final LF only |
| `record-2015-ocds-5wno2w-CE-20150000092768-23237.json` | 2026-08-17 19:33:15Z | `record?ocid=ocds-5wno2w-CE-20150000092768-23237` | 200, `application/json` | 5,274/5,275 | `67be11c8df8ee3aa212b776666707a81cf45f79ef46ff7d81a262295428bc5c5` | `e339ffa0a3f69ff63dd9a761e9b466c0f289518bb99072c9b87ae4712ca8f085` | Yes | Final LF only |
| `record-2026-ocds-5wno2w-RE-OACL-GADMSFD-2026-001-2452.json` | 2026-08-17 20:05:20Z | `record?ocid=ocds-5wno2w-RE-OACL-GADMSFD-2026-001-2452` | 200, `application/json` | 5,822/5,823 | `af13897c96cda38cb5354a99ebbc4508d3e1dcf1f98ff66a60880f3e4910b63c` | `ad77eafd46990907f407bd28c80a0904ffde3305975149f5a3408882f7a914ed` | Yes | Final LF only |
| `record-2026-ocds-5wno2w-CE-20260002969199-2455.json` | 2026-08-17 20:05:38Z | `record?ocid=ocds-5wno2w-CE-20260002969199-2455` | 200, `application/json` | 4,627/4,628 | `e5175a93a8a34fd50572e9fed3e3b9ef31f2b36bbaaeeb4c66d3b62b9e36864d` | `5a6012a30ce2242ef371214828ac169ebe2140a70e016327b2783124072ec9bc` | Yes | Final LF only |

The three record fixtures represent 2015 and 2026 and two procurement types:
catalog direct purchase and artistic/scientific/literary work. Parties in these
committed fixtures are legal entities or public institutions.

## Inspected but not committed

These responses supported bounded findings but contained unnecessary
natural-person names, tax identifiers, or addresses, or were error/presentation
artifacts. They were not cleaned or partially committed.

| Evidence | Bytes | SHA-256 | Reason not committed |
| --- | ---: | --- | --- |
| 2026 `agua` search page 1 | 5,136 | `26be421f6135766ab2ec9801492f5ef5e1e129451790f3a6ebd34ae4b449dc5f` | Personal supplier name; current-year coverage and null-field inspection only |
| 2026 `agua` search page 2 | 4,908 | `646668d997e432c7e64d5e07cda1acfda479f2ac568bd81f24ba7d3fdd9dd44b` | Pagination verification only |
| 2026 search without `search` | 6,573 | `3ddbc00b4a4003dae3360c1a62ec94c725eaa15330b4b7d7699a569432320a84` | Error/validation behavior only |
| 2026 Subasta Inversa record | 41,103 | `818013a1becccdbffe92bf26771de72054e6ca01360f900727a26c8db7aaf5a4` | Multiple natural-person tenderers and addresses |
| 2026 Concurso Público record | 27,020 | `357155ada7f523d071ac62f0e12bdac6bea42c145b80f70a609a68ac546a4bf2` | Multiple natural-person tenderers and addresses |
| Unknown-OCID HTML 404 | 6,609 | `8437bd0ef46a19c9a7c294c53e0429b40e76ebbd5fe9fd73a9025752495ddb1c` | Error page adds no reusable source fixture |

## Bulk artifacts inspected but not committed

Filters: `year=2026`, `month=7`,
`method=Obra artística, científica o literaria`. The official total endpoint
reported three procedures. All downloads were complete; no HTTP Range request
or partial sample was used.

| Format | HTTP metadata | SHA-256 | Inspection result |
| --- | --- | --- | --- |
| JSON ZIP | 3,119 bytes, `application/zip`, `Last-Modified: 2026-08-16 20:35:45Z` | `fa6405f10778039b16ff8d613a3f409b2daa26815d2a412af91db520a4a0e25f` | One 16,640-byte JSON member containing an array of three release packages |
| CSV ZIP | 4,883 bytes, `application/zip`, `Last-Modified: 2026-08-16 20:35:44Z` | `228be40c5532219d69a9020e0dec247e86679e038bcde1d07d2b38f8b50f09f8` | Eight CSV members for metadata, extensions, releases, planning, tender, awards, suppliers, contracts |
| XLSX | 19,216 bytes, spreadsheet content type, `Last-Modified: 2026-08-16 20:35:44Z` | `9db6c8a04e6e9e78131edd44f8e50d9a54f0b5ad6a425d3bfaef33536fc3ce11` | Eight analogous worksheets |

They were left uncommitted because the partition included natural-person
supplier data. Metadata and structural findings are sufficient for SPEC-002.
