"""Build source-backed excerpts for the static portfolio code inspectors."""

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://github.com/rfim/nexus-73strings/blob/main/"

# file, symbol (or whole file), language, title, description, scope
SAMPLES = {
    "postgres": ("examples/postgres_source.sql", None, "SQL", "PostgreSQL source contract",
                 "A tenant-aware relational source table. WAL LSN comes from capture metadata.",
                 "Illustrative source schema; no PostgreSQL service is deployed."),
    "feed": ("examples/feed_manifest.json", None, "JSON", "APIs & files feed metadata",
             "A named feed maps client, entity, source position and valuation fields into one contract.",
             "Inspectable configuration for the tested local adapter."),
    "debezium": ("examples/cdc_reference.py", "parse_change", "PYTHON", "CDC envelope contract",
                 "Validate tenant, key, source LSN, operation, schema version and valuation payload.",
                 "Runnable synthetic envelope parser; Debezium and Kafka Connect are not running here."),
    "manifest": ("examples/feed_config.py", "map_feed_record", "PYTHON", "Metadata-driven adapter",
                 "Map a new feed through reviewed metadata and validate it against the shared CDC contract.",
                 "Runnable adapter tested with a synthetic valuation feed."),
    "delta": ("examples/delta_cdc.sql", None, "SQL", "Azure Databricks Delta MERGE",
              "Deduplicate a source batch by tenant, entity and LSN, then update only when the source is newer.",
              "Illustrative Databricks SQL; not deployed to an Azure workspace."),
    "raw": ("examples/bronze_envelope.py", "bronze_record", "PYTHON", "Bronze trace envelope",
            "Retain the source key, LSN, operation, schema version, raw payload and capture method.",
            "Local Python reference for traceable raw history; no ADLS write is deployed."),
    "scd2": ("examples/cdc_reference.py", "scd2_versions", "PYTHON", "Silver SCD2 history",
             "Close each accepted version at the next source LSN and stop at a delete.",
             "Runnable synthetic history function with a passing behavior test."),
    "gold": ("examples/gold_valuation.sql", None, "SQL", "Gold valuation view",
            "Expose current, non-deleted valuations with tenant and source lineage.",
            "Illustrative Databricks SQL; no Gold view is deployed."),
    "quarantine": ("examples/cdc_reference.py", "apply_batch", "PYTHON", "Apply + quarantine",
                   "Invalid rows and same-LSN conflicts get reasons; valid changes apply in source order.",
                   "Runnable synthetic CDC reference with behavior tests."),
    "reconcile": ("examples/cdc_reference.py", "reconcile_delivery", "PYTHON", "Source-to-delivery reconciliation",
                  "Compare the expected rows for one tenant with the exact delivery payload.",
                  "Tested local destination check; production warehouse reads would extend it."),
    "delivery": ("examples/cdc_reference.py", "delivery_payload", "PYTHON", "Tenant-safe delivery contract",
                 "Only approved destinations receive rows filtered to the requested client tenant.",
                 "Tested local payload builder; no external warehouse connection is deployed."),
    "snowflake": ("examples/cdc_reference.py", "delivery_payload", "PYTHON", "Snowflake delivery boundary",
                  "The tested payload builder allows Snowflake and filters by client tenant.",
                  "Destination contract only; no Snowflake connector or load is deployed."),
    "sqlserver": ("examples/cdc_reference.py", "delivery_payload", "PYTHON", "SQL Server delivery boundary",
                  "The tested payload builder allows SQL Server and filters by client tenant.",
                  "Destination contract only; no SQL Server connector or load is deployed."),
    "databricks": ("examples/cdc_reference.py", "delivery_payload", "PYTHON", "Databricks delivery boundary",
                    "The tested payload builder allows Databricks and filters by client tenant.",
                    "Destination contract only; no external workspace publish is deployed."),
    "ci": (".github/workflows/ci.yml", None, "YAML", "GitHub Actions test workflow",
           "The repository runs the synthetic CDC and feed-manifest tests on pushes and pull requests.",
           "Actual CI configuration in this repository."),
    "replaytest": ("examples/test_cdc_reference.py", "test_replay_is_idempotent_and_conflict_is_quarantined",
                   "PYTHON", "Replay and conflict test",
                   "A replay leaves state unchanged; a conflicting event at the same LSN is quarantined.",
                   "Runnable unit test with synthetic events."),
}


def excerpt(path: Path, symbol: str | None) -> tuple[str, int, int]:
    lines = path.read_text().splitlines()
    if symbol is None:
        return "\n".join(lines), 1, len(lines)
    matches = [node for node in ast.walk(ast.parse("\n".join(lines)))
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == symbol]
    if len(matches) != 1:
        raise ValueError(f"Expected one {symbol} in {path}")
    node = matches[0]
    return "\n".join(lines[node.lineno - 1:node.end_lineno]), node.lineno, node.end_lineno


def main() -> None:
    data = {}
    for key, (filename, symbol, language, title, description, scope) in SAMPLES.items():
        code, first, last = excerpt(ROOT / filename, symbol)
        data[key] = {
            "title": title, "description": description, "scope": scope,
            "filename": filename, "language": language, "code": code,
            "link": f"{BASE}{filename}#L{first}-L{last}",
        }
    (ROOT / "assets/snippets.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
