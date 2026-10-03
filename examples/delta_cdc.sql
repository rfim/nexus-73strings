-- Illustrative Databricks Delta MERGE for the role's Azure platform.
-- The Python example separately tests ordering, delete and replay behavior.
MERGE INTO silver.current_valuations AS target
USING (
    SELECT tenant_id, entity_id, lsn, op, fair_value_usd, valuation_date
    FROM (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY tenant_id, entity_id ORDER BY lsn DESC
        ) AS row_rank
        FROM silver.valid_cdc_events
    ) ranked
    WHERE row_rank = 1
) AS source
ON target.tenant_id = source.tenant_id
   AND target.entity_id = source.entity_id
WHEN MATCHED AND source.lsn > target.lsn THEN UPDATE SET
    target.lsn = source.lsn,
    target.is_deleted = (source.op = 'd'),
    target.fair_value_usd = source.fair_value_usd,
    target.valuation_date = source.valuation_date
WHEN NOT MATCHED THEN INSERT (
    tenant_id, entity_id, lsn, is_deleted, fair_value_usd, valuation_date
) VALUES (
    source.tenant_id, source.entity_id, source.lsn,
    (source.op = 'd'), source.fair_value_usd, source.valuation_date
);
