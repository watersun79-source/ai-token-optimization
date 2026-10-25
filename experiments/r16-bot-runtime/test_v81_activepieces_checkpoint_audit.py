"""Synthetic adversarial tests; no real provider or Activepieces mutations."""
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from v81_activepieces_checkpoint_audit import (
    AUTOMATION_ID, SELF_REPORTED, audit_checkpoints, parse_slot, parse_utc
)

FIRST = "2026-10-22 00:00 Asia/Seoul"
LAST = "2026-10-22 21:00 Asia/Seoul"


def fixture():
    out = []
    origin = datetime(2026, 10, 22, tzinfo=ZoneInfo("Asia/Seoul"))
    for hour in range(22):
        if hour == 6:
            continue
        slot = origin + timedelta(hours=hour)
        observation = slot.astimezone(timezone.utc) + timedelta(seconds=(-98.967 if hour == 0 else 32.123))
        out.append({"cells": {
            "automationId": AUTOMATION_ID,
            "scheduledSlotKst": slot.strftime("%Y-%m-%d %H:00 Asia/Seoul"),
            "observedAtUtc": observation.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "evidenceLevel": SELF_REPORTED,
            "officialRunId": "FAKE-SELF-REPORTED-NOT-OFFICIAL" if hour < 8 or hour == 21 else "미제공",
            "readResult": "SUCCESS: SELF-REPORTED" if hour < 8 else "SELF_REPORTED_SOURCE_READ",
        }})
    return out


class CheckpointAuditTests(unittest.TestCase):
    def test_real_like_fixture_detects_1_inversion_and_1_gap(self):
        a = audit_checkpoints(fixture(), FIRST, LAST)
        self.assertEqual({"PASS": 20, "FAIL": 1, "UNVERIFIED": 1}, a["slot_counts"])
        self.assertEqual(21, a["rows_checked"])
        self.assertEqual("PRE_SLOT_OBSERVATION", a["slots"][0]["reason"])
        self.assertEqual(-98.967, a["slots"][0]["delay_seconds"])
        self.assertEqual("NO_CHECKPOINT", a["slots"][6]["reason"])
        self.assertFalse(a["native_unattended_success_verified"])
        self.assertIsNone(a["native_run_success_count"])

    def test_self_reported_official_run_id_is_never_proof(self):
        a = audit_checkpoints(fixture(), FIRST, LAST)
        self.assertEqual(8, a["claimed_run_id_fields_not_authenticated"])
        self.assertFalse(a["official_native_run_id_verified"])
        self.assertTrue(all(not row["native_execution_proven"] for row in a["slots"]))

    def test_duplicate_checkpoint_fails_closed(self):
        rows = fixture()
        rows.append(rows[-1].copy())
        a = audit_checkpoints(rows, FIRST, LAST)
        self.assertEqual("DUPLICATE_CHECKPOINTS", a["slots"][-1]["reason"])
        self.assertEqual("FAIL", a["slots"][-1]["checkpoint_status"])

    def test_wrong_automation_id_rejected(self):
        rows = fixture()
        rows[1]["cells"]["automationId"] = "OTHER"
        a = audit_checkpoints(rows, FIRST, LAST)
        self.assertEqual("WRONG_AUTOMATION", a["slots"][1]["reason"])

    def test_missing_automation_id_is_unverified(self):
        rows = fixture()
        del rows[1]["cells"]["automationId"]
        a = audit_checkpoints(rows, FIRST, LAST)
        self.assertEqual("TASK_ID_NOT_INCLUDED", a["slots"][1]["reason"])

    def test_invalid_timestamp_is_fail(self):
        rows = fixture()
        rows[1]["cells"]["observedAtUtc"] = "2026-10-21T16:01:32.1234567890Z"
        a = audit_checkpoints(rows, FIRST, LAST)
        self.assertEqual("INVALID_OBSERVED_TIME", a["slots"][1]["reason"])

    def test_self_declared_trusted_origin_not_authenticated(self):
        rows = fixture()
        rows[1]["cells"]["evidenceLevel"] = "OFFICIAL_NATIVE_ATTESTED"
        a = audit_checkpoints(rows, FIRST, LAST)
        self.assertEqual("SELF_REPORTED_ORIGIN_NOT_CONFIRMED", a["slots"][1]["reason"])
        self.assertFalse(a["native_unattended_success_verified"])

    def test_out_of_window_and_malformed_rows_cannot_pass(self):
        rows = fixture() + [{"cells": {"scheduledSlotKst":"2099-01-01 00:00 Asia/Seoul"}},
                            {"cells": {"scheduledSlotKst":[]}}, {}]
        a = audit_checkpoints(rows, FIRST, LAST)
        self.assertEqual(3, a["out_of_window_or_malformed_rows"])
        self.assertEqual({"PASS":20,"FAIL":1,"UNVERIFIED":1},a["slot_counts"])

    def test_all_missing_is_not_a_native_failure_assertion(self):
        a = audit_checkpoints([], FIRST, LAST)
        self.assertEqual(22, a["slot_counts"]["UNVERIFIED"])
        self.assertEqual(0, a["slot_counts"]["FAIL"])
        self.assertFalse(a["native_unattended_success_verified"])

    def test_invalid_windows_fail(self):
        for start, end in (("broken",LAST),(LAST,FIRST),(FIRST,"2026-11-01 21:00 Asia/Seoul")):
            with self.subTest(start=start,end=end), self.assertRaises(ValueError):
                audit_checkpoints([],start,end)

    def test_boolean_fields_and_malformed_types_no_provider_success(self):
        rows=fixture()
        rows[1]["cells"]["automationId"]=True
        self.assertEqual("WRONG_AUTOMATION",audit_checkpoints(rows,FIRST,LAST)["slots"][1]["reason"])
        with self.assertRaises(ValueError):
            audit_checkpoints("not rows",FIRST,LAST)

    def test_parsers_reject_bad_timezone_and_fraction(self):
        self.assertIsNone(parse_slot("2026-10-22 00:00 UTC"))
        self.assertIsNone(parse_utc("2026-10-21T15:00:00+09:00"))
        self.assertIsNotNone(parse_utc("2026-10-21T15:00:00.123456789Z"))
        self.assertIsNone(parse_utc("2026-10-21T15:00:00.1234567890Z"))
        self.assertIsNotNone(parse_utc("2026-10-21T15:00:00Z"))


if __name__ == "__main__":
    unittest.main()
