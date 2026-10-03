"""A small metadata-driven adapter for a synthetic private-markets feed."""

import json
from pathlib import Path

from cdc_reference import parse_change


REQUIRED = frozenset({"tenant_field", "entity_field", "position_field",
                      "operation_field", "after_field", "schema_version"})


def load_manifest(path: str | Path) -> dict:
    manifest = json.loads(Path(path).read_text())
    for name, config in manifest.items():
        if not REQUIRED.issubset(config):
            raise ValueError(f"feed {name} is missing required metadata")
    return manifest


def map_feed_record(record: dict, config: dict) -> dict:
    """Make a new feed a mapping, while keeping the common CDC contract."""
    if not REQUIRED.issubset(config):
        raise ValueError("feed is missing required metadata")
    envelope = {
        "tenant_id": record[config["tenant_field"]],
        "entity_id": record[config["entity_field"]],
        "lsn": record[config["position_field"]],
        "op": record[config["operation_field"]],
        "after": record.get(config["after_field"]),
        "schema_version": config["schema_version"],
    }
    parse_change(envelope)
    return envelope
