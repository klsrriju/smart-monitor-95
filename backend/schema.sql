-- SmartMonitor PostgreSQL compatibility schema.
-- The combined gateway can use this JSONB table immediately.
-- It preserves one stable collection/API contract while the UI is migrated.
CREATE TABLE IF NOT EXISTS smartmonitor_records (
    collection TEXT NOT NULL,
    record_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (collection, record_id)
);
CREATE INDEX IF NOT EXISTS idx_sm_collection ON smartmonitor_records(collection);
CREATE INDEX IF NOT EXISTS idx_sm_updated_at ON smartmonitor_records(updated_at DESC);
