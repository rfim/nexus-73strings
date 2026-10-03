-- Illustrative PostgreSQL source table; WAL LSN belongs to capture metadata.
CREATE TABLE portfolio_valuations (
    tenant_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    fair_value_usd NUMERIC(24, 2) NOT NULL,
    valuation_date DATE NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, entity_id)
);
