-- Create source-neutral raw evidence storage.
-- depends:

CREATE TABLE raw_evidence (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    source_key TEXT,
    endpoint TEXT NOT NULL,
    parameters JSONB NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    http_status INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    payload_byte_size BIGINT NOT NULL,
    payload BYTEA NOT NULL,
    etag TEXT,
    last_modified TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
