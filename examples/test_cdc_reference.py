"""Behavior tests for the synthetic CDC portfolio reference."""

import unittest

from cdc_reference import (apply_batch, delivery_payload, reconcile_delivery,
                           scd2_versions, visible_for_tenant)


def event(tenant="client-a", entity="asset-1", lsn=1, value="100.00", op="u"):
    return {"tenant_id": tenant, "entity_id": entity, "lsn": lsn, "op": op,
            "schema_version": 1,
            "after": None if op == "d" else {"fair_value_usd": value,
                                               "valuation_date": "2026-09-30"}}


class CdcReferenceTests(unittest.TestCase):
    def test_out_of_order_changes_keep_highest_lsn(self):
        outcome = apply_batch({}, [event(lsn=3, value="130"), event(lsn=1),
                                   event(lsn=2, value="120")])
        self.assertEqual(visible_for_tenant(outcome.state, "client-a")[0]["fair_value_usd"], "130")
        self.assertEqual(outcome.applied, 3)
        self.assertTrue(outcome.reconciles(3))

    def test_replay_is_idempotent_and_conflict_is_quarantined(self):
        batch = [event(lsn=5, value="125")]
        first = apply_batch({}, batch)
        replay = apply_batch(first.state, batch)
        conflict = apply_batch(first.state, [event(lsn=5, value="999")])
        self.assertEqual(replay.state, first.state)
        self.assertEqual(replay.replayed_or_stale, 1)
        self.assertEqual(conflict.state, first.state)
        self.assertEqual(conflict.quarantined[0].reason, "conflicting event at same LSN")
        self.assertTrue(conflict.reconciles(1))

    def test_delete_survives_stale_replay(self):
        state = apply_batch({}, [event(lsn=1), event(lsn=3, op="d")]).state
        self.assertEqual(visible_for_tenant(state, "client-a"), [])
        replay = apply_batch(state, [event(lsn=2, value="200")])
        self.assertEqual(visible_for_tenant(replay.state, "client-a"), [])
        self.assertEqual(replay.replayed_or_stale, 1)

    def test_bad_row_is_quarantined_and_other_tenant_stays_isolated(self):
        bad = event(entity="bad", lsn=2, value="NaN")
        outcome = apply_batch({}, [event(), bad, event(tenant="client-b", value="500")])
        self.assertEqual(outcome.applied, 2)
        self.assertEqual(len(outcome.quarantined), 1)
        self.assertTrue(outcome.reconciles(3))
        self.assertEqual(len(visible_for_tenant(outcome.state, "client-a")), 1)
        self.assertEqual(len(visible_for_tenant(outcome.state, "client-b")), 1)
        self.assertEqual(visible_for_tenant(outcome.state, "client-a")[0]["fair_value_usd"], "100.00")

    def test_scd2_intervals_close_on_update_and_delete(self):
        history = scd2_versions([event(lsn=1), event(lsn=4, value="140"),
                                 event(lsn=6, op="d")], "client-a", "asset-1")
        self.assertEqual([item["valid_from_lsn"] for item in history], [1, 4])
        self.assertEqual([item["valid_to_lsn"] for item in history], [4, 6])

    def test_delivery_contract_filters_tenant_and_destination(self):
        state = apply_batch({}, [event(tenant="client-a"),
                                 event(tenant="client-b", entity="asset-2")]).state
        delivered = delivery_payload(state, "client-a", "snowflake")
        self.assertTrue(reconcile_delivery(state, delivered))
        self.assertEqual(len(delivered["rows"]), 1)
        self.assertEqual(delivered["rows"][0]["entity_id"], "asset-1")
        delivered["rows"].append(visible_for_tenant(state, "client-b")[0])
        self.assertFalse(reconcile_delivery(state, delivered))
        with self.assertRaises(ValueError):
            delivery_payload(state, "client-a", "unknown_sink")


if __name__ == "__main__":
    unittest.main()
