"""Synthetic CDC reference for a 73 Strings portfolio case study.

This local Python example is separate from Lifepal production code. It models
ordering, deletes, replay, row-level quarantine and tenant-scoped reads.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Change:
    tenant_id: str
    entity_id: str
    lsn: int
    operation: str
    fair_value_usd: Decimal | None
    valuation_date: str | None


@dataclass(frozen=True)
class CurrentRow:
    lsn: int
    deleted: bool
    fair_value_usd: Decimal | None
    valuation_date: str | None


@dataclass(frozen=True)
class RejectedRow:
    raw: dict
    reason: str


@dataclass(frozen=True)
class BatchOutcome:
    state: dict[tuple[str, str], CurrentRow]
    applied: int
    replayed_or_stale: int
    quarantined: tuple[RejectedRow, ...]

    def reconciles(self, received: int) -> bool:
        return self.applied + self.replayed_or_stale + len(self.quarantined) == received


def parse_change(raw: dict) -> Change:
    """Validate one CDC envelope before any row is published."""
    tenant_id = raw.get("tenant_id")
    entity_id = raw.get("entity_id")
    lsn = raw.get("lsn")
    op = raw.get("op")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise ValueError("tenant_id is required")
    if not isinstance(entity_id, str) or not entity_id.strip():
        raise ValueError("entity_id is required")
    if isinstance(lsn, bool) or not isinstance(lsn, int) or lsn < 1:
        raise ValueError("lsn must be a positive integer")
    if op not in {"c", "u", "r", "d"}:
        raise ValueError("unsupported CDC operation")
    if raw.get("schema_version") != 1:
        raise ValueError("unsupported schema version")
    if op == "d":
        return Change(tenant_id, entity_id, lsn, op, None, None)

    after = raw.get("after")
    if not isinstance(after, dict):
        raise ValueError("upsert needs an after image")
    try:
        fair_value = Decimal(str(after["fair_value_usd"]))
        valuation_date = date.fromisoformat(after["valuation_date"]).isoformat()
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid fair value or valuation date") from exc
    if not fair_value.is_finite() or fair_value < 0:
        raise ValueError("fair value must be finite and non-negative")
    return Change(tenant_id, entity_id, lsn, op, fair_value, valuation_date)


def apply_batch(prior: dict[tuple[str, str], CurrentRow], raw_events: list[dict]) -> BatchOutcome:
    """Apply valid changes by source log position; quarantine invalid rows."""
    state = dict(prior)
    valid: list[Change] = []
    rejected: list[RejectedRow] = []
    for raw in raw_events:
        try:
            valid.append(parse_change(raw))
        except (AttributeError, TypeError, ValueError) as exc:
            rejected.append(RejectedRow(raw, str(exc)))

    applied = replayed = 0
    for change in sorted(valid, key=lambda item: (item.tenant_id, item.entity_id, item.lsn)):
        key = (change.tenant_id, change.entity_id)
        current = state.get(key)
        if current and change.lsn < current.lsn:
            replayed += 1
            continue
        candidate = CurrentRow(change.lsn, change.operation == "d",
                               change.fair_value_usd, change.valuation_date)
        if current and change.lsn == current.lsn:
            if candidate == current:
                replayed += 1
            else:
                rejected.append(RejectedRow({"tenant_id": change.tenant_id,
                                             "entity_id": change.entity_id,
                                             "lsn": change.lsn}, "conflicting event at same LSN"))
            continue
        state[key] = candidate
        applied += 1
    return BatchOutcome(state, applied, replayed, tuple(rejected))


def visible_for_tenant(state: dict[tuple[str, str], CurrentRow], tenant_id: str) -> list[dict]:
    """Expose only active rows belonging to the requested client tenant."""
    if not tenant_id:
        raise ValueError("tenant_id is required")
    return [
        {"tenant_id": row_tenant, "entity_id": entity_id,
         "fair_value_usd": str(row.fair_value_usd),
         "valuation_date": row.valuation_date, "source_lsn": row.lsn}
        for (row_tenant, entity_id), row in sorted(state.items())
        if row_tenant == tenant_id and not row.deleted
    ]


DESTINATIONS = frozenset({"snowflake", "sql_server", "databricks"})


def delivery_payload(state: dict[tuple[str, str], CurrentRow], tenant_id: str,
                     destination: str) -> dict:
    """Build a tenant-scoped contract for an approved sink; no network write."""
    if destination not in DESTINATIONS:
        raise ValueError("destination is not approved")
    return {"tenant_id": tenant_id, "destination": destination,
            "rows": visible_for_tenant(state, tenant_id)}


def reconcile_delivery(state: dict[tuple[str, str], CurrentRow], payload: dict) -> bool:
    """Compare the tenant-scoped expected rows with a delivery payload."""
    if payload.get("destination") not in DESTINATIONS:
        return False
    tenant_id = payload.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id:
        return False
    expected = visible_for_tenant(state, tenant_id)
    actual = payload.get("rows")
    if not isinstance(actual, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("entity_id"), str)
        for row in actual
    ):
        return False
    return expected == sorted(actual, key=lambda row: row["entity_id"])


def scd2_versions(raw_events: list[dict], tenant_id: str, entity_id: str) -> list[dict]:
    """Build a simple LSN-bounded history for one tenant and entity."""
    changes = sorted((parse_change(raw) for raw in raw_events
                      if raw.get("tenant_id") == tenant_id and raw.get("entity_id") == entity_id),
                     key=lambda item: item.lsn)
    versions: list[dict] = []
    for change in changes:
        if versions and change.lsn <= versions[-1]["valid_from_lsn"]:
            continue
        if versions and versions[-1]["valid_to_lsn"] is None:
            versions[-1]["valid_to_lsn"] = change.lsn
        if change.operation != "d":
            versions.append({"valid_from_lsn": change.lsn, "valid_to_lsn": None,
                             "fair_value_usd": str(change.fair_value_usd),
                             "valuation_date": change.valuation_date})
    return versions
