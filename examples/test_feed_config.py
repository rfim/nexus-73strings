"""Tests for the metadata-driven source mapping."""

from pathlib import Path
import unittest

from feed_config import load_manifest, map_feed_record


class FeedConfigTests(unittest.TestCase):
    def test_configured_feed_maps_to_common_contract(self):
        config = load_manifest(Path(__file__).with_name("feed_manifest.json"))["portfolio_valuations"]
        raw = {"client_id": "client-a", "portfolio_company_id": "company-7",
               "source_lsn": 20, "change_kind": "u",
               "valuation": {"fair_value_usd": "25000000.00",
                             "valuation_date": "2026-09-30"}}
        mapped = map_feed_record(raw, config)
        self.assertEqual((mapped["tenant_id"], mapped["entity_id"], mapped["lsn"]),
                         ("client-a", "company-7", 20))

    def test_missing_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            map_feed_record({"client_id": "client-a"}, {"tenant_field": "client_id"})


if __name__ == "__main__":
    unittest.main()
