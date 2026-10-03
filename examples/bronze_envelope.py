"""Illustrative raw-history envelope for a source event."""

from datetime import datetime, timezone


def bronze_record(raw: dict, capture_method: str) -> dict:
    """Retain source identity and payload for traceable reprocessing."""
    if not capture_method:
        raise ValueError("capture method is required")
    return {
        "tenant_id": raw["tenant_id"],
        "entity_id": raw["entity_id"],
        "source_lsn": raw["lsn"],
        "operation": raw["op"],
        "schema_version": raw["schema_version"],
        "raw_payload": raw.get("after"),
        "capture_method": capture_method,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
