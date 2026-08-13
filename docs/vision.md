# Public Intelligence — Project Vision

**Version:** 0.1  
**Status:** Draft  
**Project stage:** Hobby / validation

## 1. Vision

Build an extensible platform that transforms fragmented public information into structured, searchable, and actionable business intelligence.

The long-term opportunity is not merely to aggregate public datasets. The platform should help answer questions such as:

- What happened?
- Who is involved?
- Is this unusual?
- Could this represent an opportunity?
- What changed compared with historical behavior?
- What might deserve attention?

## 2. Initial context

Public institutions publish potentially valuable information through APIs, downloadable datasets, web pages, documents, registries, and other channels.

The information is often:

- fragmented across institutions
- represented in different formats
- difficult to search historically
- difficult to relate across sources
- presented as documents rather than business events
- useful only after significant manual interpretation

This creates an opportunity to build a reusable intelligence layer over public information.

## 3. Product hypothesis

If public information can be collected, normalized, connected over time, and interpreted responsibly, it may generate useful intelligence for businesses, analysts, consultants, suppliers, and other professional users.

The platform will initially focus on three capabilities.

### 3.1 Opportunity Intelligence

Identify potentially actionable opportunities from public information.

Initial example:

- relevant public procurement processes

Future examples may include:

- regulatory approvals
- newly registered products
- permits
- public calls
- market-entry signals

### 3.2 Company Intelligence

Build a historical view of observable public activity related to a company or organization.

Possible information may include:

- public procurement activity
- contracts and awards
- regulatory registrations
- products
- corporate changes
- relationships with public institutions
- historical events

### 3.3 Business Signals

Detect meaningful patterns or changes from facts and historical behavior.

Examples:

- procurement activity spike
- product portfolio expansion
- new regulatory activity
- recurring purchasing pattern
- unusually frequent awards
- entry into a new category

Signals are interpretations, not source facts. The platform must preserve that distinction.

## 4. Core domain language

### Source

An external origin of public information.

Examples:

- SERCOP
- regulatory registries
- corporate registries
- open-data portals

### Entity

A real-world subject that information refers to.

Examples:

- Company
- GovernmentOrganization
- PublicInstitution
- Product

### Event

A factual occurrence observed from a source.

Examples:

- PROCUREMENT_PUBLISHED
- CONTRACT_AWARDED
- RSU_APPROVED
- RSU_REVOKED
- ADMINISTRATOR_CHANGED

An event should retain provenance.

### Opportunity

A potentially actionable situation derived from public information.

An opportunity may originate directly from an event or from a combination of data and rules.

### Signal

A derived interpretation produced from events, history, rules, statistics, or future analytical models.

Example:

A company receiving four awards in thirty days is factual data.

`PROCUREMENT_ACTIVITY_SPIKE` is a derived signal.

## 5. Initial technical direction

The project will begin as a modular monolith.

The initial high-level flow is:

```text
External Sources
      |
      v
  Connectors
      |
      v
 Raw Storage
      |
      v
Normalization
      |
      v
 Domain Model
      |
      v
Events / History
      |
      v
Rules / Analytics
      |
      v
Signals / Opportunities
      |
      v
 API / Future UI / Alerts
```

External source details must remain outside the core domain.

## 6. Data strategy

Where practical, the platform should preserve both:

1. source/raw representation
2. normalized/internal representation

Raw preservation allows future reprocessing when:

- normalization rules improve
- previously ignored fields become relevant
- bugs are discovered
- new intelligence features require historical attributes

The raw layer is evidence, not the domain model.

## 7. First source

SERCOP procurement data is the proposed first source.

Reasons:

- clear business relevance
- structured public procurement data exists
- historical analysis has potential value
- useful signals can be built without machine learning
- procurement is a good domain for validating ingestion, normalization, entity resolution, and historical analysis

The architecture must not become a SERCOP-specific application.

## 8. Future sources

Future sources may include, depending on feasibility and legal/technical access:

- company information
- regulatory registrations
- RSU information
- ARCSA-related registries
- SENADI-related information
- customs/import-related public information
- additional government open-data sources

Every new source should enter through a connector boundary.

## 9. Intelligence philosophy

AI is not the foundation of the platform.

Preferred order:

```text
Good data
  -> history
  -> deterministic rules
  -> analytics
  -> AI-assisted interpretation
```

LLMs may later help with:

- natural-language queries
- document understanding
- summarization
- explanation of signals
- classification
- research assistance

LLMs must not become the authoritative source of factual platform data.

## 10. Product philosophy

This project begins as a serious hobby and learning project.

Commercialization is a hypothesis to validate, not an assumption.

The project is successful initially if it:

- is enjoyable to build
- develops strong engineering practices
- demonstrates real data-engineering and AI capabilities
- produces genuinely useful intelligence from public data
- can evolve without major rewrites
- becomes a strong portfolio project even if it is never commercialized

## 11. Commercial hypotheses

Potential future business models include:

- subscription intelligence
- company monitoring
- procurement opportunity alerts
- regulatory intelligence
- premium reports
- data/API access
- industry-specific intelligence products

No monetization model is selected at version 0.1.

## 12. Non-goals

At the current stage, the project is not intended to:

- replicate every government portal
- ingest every available public source
- become a generic web-scraping platform
- use microservices
- introduce Kafka or distributed infrastructure without demonstrated need
- build an AI chatbot before reliable data exists
- predict outcomes without sufficient historical evidence
- store unnecessary personal information
- bypass access controls or source restrictions
- implement enterprise-scale authentication, billing, or multi-tenancy

## 13. Engineering principles

1. Simple before distributed.
2. Domain before framework.
3. Facts before AI interpretations.
4. Raw data before irreversible transformations.
5. Source adapters before source coupling.
6. Rules before premature ML.
7. Tests before autonomous refactors.
8. Specs before substantial implementation.
9. ADRs for meaningful architectural decisions.
10. Build only what the current milestone needs.

## 14. Initial milestones

### Milestone 0 — Build the Harness

Establish:

- repository structure
- AGENTS.md
- project vision
- ADR process
- spec process
- Python tooling
- tests and quality checks
- minimal application foundation

### Milestone 1 — First Real Intelligence

Using SERCOP data:

- ingest real public procurement data
- preserve raw source information
- normalize relevant procurement concepts
- store historical information
- expose basic search/query capability
- generate at least one useful deterministic business signal

Example candidate signals:

- `PROCUREMENT_ACTIVITY_SPIKE`
- `RECURRING_PURCHASE_PATTERN`

## 15. Main architectural test

A major test of the architecture will be adding a second materially different source.

For example:

```text
connectors/
    sercop/
    rsu/
```

If the second source can be introduced without redesigning the core system, the initial architecture is doing its job.

## 16. Open questions

These questions are intentionally unresolved:

- Which SERCOP access strategy should be used for initial historical ingestion?
- What minimum entity-resolution strategy is required?
- How should raw payloads be persisted initially?
- What is the first commercially meaningful signal?
- Which source should become the second connector?
- When is a web UI justified?
- When, if ever, should AI become part of the runtime product?

These questions should be resolved through research, experiments, specs, and ADRs rather than assumptions.
