-- Illustrative Databricks SQL view over a validated Delta Silver table.
CREATE OR REPLACE VIEW gold.latest_portfolio_valuations AS
SELECT
    tenant_id,
    entity_id,
    fair_value_usd,
    valuation_date,
    lsn AS source_lsn
FROM silver.current_valuations
WHERE is_deleted = false;
