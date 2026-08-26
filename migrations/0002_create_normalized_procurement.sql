-- Create source-independent normalized procurement snapshot storage.
-- depends: 0001_create_raw_evidence

CREATE TABLE procurements (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    evidence_id UUID,
    buyer_present BOOLEAN NOT NULL,
    buyer_external_id TEXT,
    buyer_name TEXT,
    procedure_external_id TEXT,
    procedure_title TEXT,
    procedure_description TEXT,
    procedure_status TEXT,
    procedure_method TEXT,
    procedure_method_details TEXT,
    procedure_category TEXT,
    procedure_value_amount NUMERIC,
    procedure_value_currency TEXT,
    suppliers_present BOOLEAN NOT NULL,
    awards_present BOOLEAN NOT NULL,
    contracts_present BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT procurements_source_external_id_key
        UNIQUE (source, external_id),
    CONSTRAINT procurements_evidence_id_fkey
        FOREIGN KEY (evidence_id)
        REFERENCES raw_evidence (id)
        ON DELETE RESTRICT,
    CONSTRAINT procurements_missing_buyer_check
        CHECK (
            buyer_present
            OR (buyer_external_id IS NULL AND buyer_name IS NULL)
        ),
    CONSTRAINT procurements_procedure_money_check
        CHECK (
            procedure_value_amount IS NOT NULL
            OR procedure_value_currency IS NULL
        )
);

CREATE TABLE procurement_suppliers (
    procurement_id UUID NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    external_id TEXT,
    name TEXT,
    PRIMARY KEY (procurement_id, ordinal),
    FOREIGN KEY (procurement_id)
        REFERENCES procurements (id)
        ON DELETE CASCADE
);

CREATE TABLE procurement_awards (
    procurement_id UUID NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    external_id TEXT NOT NULL,
    status TEXT,
    award_date TIMESTAMPTZ,
    value_amount NUMERIC,
    value_currency TEXT,
    suppliers_present BOOLEAN NOT NULL,
    PRIMARY KEY (procurement_id, ordinal),
    FOREIGN KEY (procurement_id)
        REFERENCES procurements (id)
        ON DELETE CASCADE,
    CHECK (value_amount IS NOT NULL OR value_currency IS NULL)
);

CREATE TABLE award_suppliers (
    procurement_id UUID NOT NULL,
    award_ordinal INTEGER NOT NULL CHECK (award_ordinal >= 0),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    external_id TEXT,
    name TEXT,
    PRIMARY KEY (procurement_id, award_ordinal, ordinal),
    FOREIGN KEY (procurement_id, award_ordinal)
        REFERENCES procurement_awards (procurement_id, ordinal)
        ON DELETE CASCADE
);

CREATE TABLE procurement_contracts (
    procurement_id UUID NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    external_id TEXT NOT NULL,
    award_external_id TEXT,
    status TEXT,
    date_signed TIMESTAMPTZ,
    value_amount NUMERIC,
    value_currency TEXT,
    PRIMARY KEY (procurement_id, ordinal),
    FOREIGN KEY (procurement_id)
        REFERENCES procurements (id)
        ON DELETE CASCADE,
    CHECK (value_amount IS NOT NULL OR value_currency IS NULL)
);
