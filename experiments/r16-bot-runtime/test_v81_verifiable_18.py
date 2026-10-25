"""Offline positive + adversarial tests for *alternative*, not native 18."""
from __future__ import annotations
import json
import unittest

import v81_verifiable_18 as v


def fake_snapshot():
    """All values invented. No provider data, credentials or user ID injected."""
    sha = "a" * 40
    rid = 12345
    c = "2026-10-25T01:35:29Z"
    jst = "2026-10-25T01:35:31Z"
    jend = "2026-10-25T01:35:43Z"
    steps = [
        {"name": "Fetch CI-verified R16 sources (pinned SHA)", "conclusion": "success"},
        {"name": "Install offline role wrappers and validate all 100 rules", "conclusion": "success"},
        {"name": "Verify receipt and never claim native ChatGPT automation proof", "conclusion": "success"},
    ]
    messages = [
        f"2026-10-25T01:35:32Z ref: {v.PINNED_SHA}",
        f"2026-10-25T01:35:36Z git checkout --progress --force {v.PINNED_SHA}",
        '2026-10-25T01:35:39Z '+json.dumps({"source":"local_measured_tests", "counts":{"python":{"passed":22,"total":22}, "java":{"passed":20,"total":20}, "js":{"passed":20,"total":20}}}),
        '2026-10-25T01:35:39Z '+json.dumps({"mode":"OFFLINE_SINGLE_PROCESS_100_RULE_CHECKS_NOT_100_LLM_MODELS", "executed_rule_checks":100,"statuses":{"PASS":82,"UNVERIFIED":18}}),
        '2026-10-25T01:35:39Z '+json.dumps({"kind":"OFFLINE_BACKGROUND_LOOP_NOT_NATIVE_RESERVATION", "official_unattended_app_call_success":"UNVERIFIED", "selected_outcome":"UNVERIFIED"}),
        "2026-10-25T01:35:39Z R16_HOURLY_OFFLINE_RECEIPT_VALIDATED",
    ]
    return {"run":{"path":v.WORKFLOW,"event":"schedule","id":rid,
                   "html_url":f"https://github.com/{v.REPO}/actions/runs/{rid}",
                   "head_sha":sha,"status":"completed","conclusion":"success","created_at":c},
            "job":{"id":98765,"run_id":rid,"status":"completed","conclusion":"success",
                   "started_at":jst,"completed_at":jend,"steps":steps},
            "main_sha":sha,"inferred_slot_utc":"2026-10-25T01:15:00Z",
            "raw_job_log":"\n".join(messages)}


def statuses(snapshot):
    return {r["id"]:r["status"] for r in v.evaluate(snapshot)["roles"]}


class Substitutes(unittest.TestCase):
    def test_all_18_local_input_consistency_checks_pass_on_synthetic_fixture(self):
        out=v.evaluate(fake_snapshot())
        self.assertEqual(18, len(out["roles"]))
        self.assertEqual({"PASS":18,"FAIL":0,"UNVERIFIED":0}, out["statuses"])
        self.assertFalse(out["native_chatgpt_same_run_proven"])
        self.assertEqual("UNVERIFIED", out["original_native_evidence_gate_status"])
        self.assertEqual(18,len(out["original_native_evidence_gates_retained"]))

    def test_empty_snapshot_is_all_unverified(self):
        self.assertEqual(18,v.evaluate({})["statuses"]["UNVERIFIED"])

    def test_sanitized_snapshot_is_not_considered_official_provider_attestation(self):
        result=v.evaluate(fake_snapshot())
        self.assertEqual("UNSIGNED_SNAPSHOT_VALIDATE_WITH_AUTHENTICATED_CONNECTOR",result["source_input_trust"])

    def test_each_new_rule_rejects_an_adversarial_change(self):
        changes = {
            "V01": lambda s:s["run"].update(path=".github/workflows/other.yml"),
            "V02": lambda s:s["run"].update(event="push"),
            "V03": lambda s:s["run"].update(html_url="https://github.com/other"),
            "V04": lambda s:s.update(main_sha="b"*40),
            "V05": lambda s:s["run"].update(conclusion="failure"),
            "V06": lambda s:s["run"].update(created_at="not-a-time"),
            "V07": lambda s:s.update(inferred_slot_utc="2026-10-24T23:15:00Z"),
            "V08": lambda s:s["job"].update(run_id=99999),
            "V09": lambda s:s["job"].update(status="queued"),
            "V10": lambda s:s["job"].update(completed_at="2026-10-25T01:34:29Z"),
            "V11": lambda s:s["job"]["steps"][0].update(conclusion="failure"),
            "V12": lambda s:s["job"].update(started_at="2026-10-25T01:34:00Z"),
            "V13": lambda s:s.update(raw_job_log=s["raw_job_log"].replace("git checkout --progress --force", "git checkout --progress --fake")),
            "V14": lambda s:s.update(raw_job_log=s["raw_job_log"].replace('"python": {"passed": 22', '"python": {"passed": 21')),
            "V15": lambda s:s.update(raw_job_log=s["raw_job_log"].replace('"java": {"passed": 20', '"java": {"passed": 19')),
            "V16": lambda s:s.update(raw_job_log=s["raw_job_log"].replace('"js": {"passed": 20', '"js": {"passed": 19')),
            "V17": lambda s:s.update(raw_job_log=s["raw_job_log"].replace('"UNVERIFIED": 18','"UNVERIFIED": 17')),
            "V18": lambda s:s.update(raw_job_log=s["raw_job_log"].replace('"selected_outcome": "UNVERIFIED"','"selected_outcome": "PASS"')),
        }
        self.assertEqual(set(v.NEW_IDS),set(changes))
        for name,modify in changes.items():
            with self.subTest(rule=name):
                s=fake_snapshot();modify(s)
                self.assertEqual("FAIL",statuses(s)[name])

    def test_missing_log_is_unverified_not_fake_pass(self):
        s=fake_snapshot();s.pop("raw_job_log")
        statuses_by_id=statuses(s)
        for i in range(13,19):
            self.assertEqual("UNVERIFIED",statuses_by_id[f"V{i:02d}"])

    def test_unchanged_legacy_gate_identity_is_not_reused(self):
        source=[]
        prefixes="SGPLAOCMTE"
        for prefix in prefixes:
            for n in range(1,11):
                source.append({"id":f"{prefix}{n:02d}","name":f"source {prefix}{n:02d}","category":"offline"})
        manifest=v.alternate_manifest(source)
        self.assertEqual(100,manifest["total_roles"])
        ids={r["id"] for r in manifest["roles"]}
        self.assertEqual(100,len(ids))
        self.assertFalse(ids.intersection(v.OLD_NATIVE_IDS))
        self.assertEqual(set(v.NEW_IDS), ids-{x["id"] for x in source if x["id"] not in v.OLD_NATIVE_IDS})
        self.assertEqual(18,len(manifest["untouched_native_gates"]))

    def test_missing_catalog_role_rejected(self):
        x=[]
        with self.assertRaises(ValueError):v.alternate_manifest(x)

    def test_boolean_run_id_cannot_be_a_valid_positive_id(self):
        s=fake_snapshot();s["run"]["id"]=True
        self.assertEqual("FAIL", statuses(s)["V03"])

    def test_forged_native_success_flag_is_never_taken_as_proof(self):
        s=fake_snapshot();s["native_chatgpt_same_run_proven"]=True
        r=v.evaluate(s)
        self.assertFalse(r["native_chatgpt_same_run_proven"])
        self.assertEqual("UNVERIFIED",r["original_native_evidence_gate_status"])

    def test_v17_rejects_string_failure_and_unknown_or_boolean_counts(self):
        base = fake_snapshot()
        candidates = (
            ('"UNVERIFIED": 18}', '"UNVERIFIED": 18, "FAIL": "1"}'),
            ('"UNVERIFIED": 18}', '"UNVERIFIED": 18, "EXTRA": 0}'),
            ('"PASS": 82', '"PASS": true'),
            ('"executed_rule_checks": 100', '"executed_rule_checks": true'),
        )
        for before, after in candidates:
            with self.subTest(after=after):
                x = fake_snapshot()
                self.assertIn(before, x["raw_job_log"])
                x["raw_job_log"] = x["raw_job_log"].replace(before, after)
                self.assertEqual("FAIL", statuses(x)["V17"])

    def test_v06_rejects_excessive_fractional_precision(self):
        for fraction in ("1" * 7, "1" * 30):
            with self.subTest(length=len(fraction)):
                x = fake_snapshot()
                x["run"]["created_at"] = "2026-10-25T01:35:29."+fraction+"Z"
                self.assertEqual("FAIL", statuses(x)["V06"])
        for fraction in ("1", "123456"):
            x = fake_snapshot()
            x["run"]["created_at"] = "2026-10-25T01:35:29."+fraction+"Z"
            self.assertEqual("PASS", statuses(x)["V06"])

    def test_v18_requires_actual_receipt_output_not_command_echo(self):
        s = fake_snapshot()
        s["raw_job_log"] = s["raw_job_log"].replace(
            "2026-10-25T01:35:39Z R16_HOURLY_OFFLINE_RECEIPT_VALIDATED",
            "2026-10-25T01:35:39Z Run python -c 'print(\"R16_HOURLY_OFFLINE_RECEIPT_VALIDATED\")'"
        )
        self.assertEqual("FAIL", statuses(s)["V18"])
        s = fake_snapshot()
        s["raw_job_log"] = s["raw_job_log"].replace(
            "2026-10-25T01:35:39Z R16_HOURLY_OFFLINE_RECEIPT_VALIDATED",
            "2026-10-25T01:35:39.8553230Z R16_HOURLY_OFFLINE_RECEIPT_VALIDATED"
        )
        self.assertEqual("PASS", statuses(s)["V18"])

    def test_v13_rejects_echoed_checkout_commands(self):
        s = fake_snapshot()
        s["raw_job_log"] = s["raw_job_log"].replace(
            "2026-10-25T01:35:32Z ref: "+v.PINNED_SHA,
            "2026-10-25T01:35:32Z Run echo 'ref: "+v.PINNED_SHA+"'")
        self.assertEqual("FAIL", statuses(s)["V13"])
        s = fake_snapshot()
        s["raw_job_log"] = s["raw_job_log"].replace(
            "2026-10-25T01:35:36Z git checkout --progress --force "+v.PINNED_SHA,
            "2026-10-25T01:35:36Z Run echo 'git checkout --progress --force "+v.PINNED_SHA+"'")
        self.assertEqual("FAIL", statuses(s)["V13"])

    def test_log_payload_rejects_echoed_json_not_emitted_json(self):
        for identifier, token in (("V14", '"source": "local_measured_tests"'),
                                  ("V17", '"mode": "OFFLINE_SINGLE_PROCESS_100_RULE_CHECKS_NOT_100_LLM_MODELS"'),
                                  ("V18", '"kind": "OFFLINE_BACKGROUND_LOOP_NOT_NATIVE_RESERVATION"')):
            with self.subTest(identifier=identifier):
                s = fake_snapshot()
                lines = s["raw_job_log"].splitlines()
                lines = [line.replace("Z {", "Z Run echo '{") + "'" if token in line else line
                         for line in lines]
                s["raw_job_log"] = "\n".join(lines)
                self.assertEqual("UNVERIFIED", statuses(s)[identifier])

    def test_log_duplicate_measured_event_is_ambiguous(self):
        s = fake_snapshot()
        original_line = next(x for x in s["raw_job_log"].splitlines() if '"source": "local_measured_tests"' in x)
        conflicting = original_line.replace('"passed": 22', '"passed": 21')
        s["raw_job_log"] += "\n" + conflicting
        self.assertEqual("UNVERIFIED", statuses(s)["V14"])
        self.assertEqual("UNVERIFIED", statuses(s)["V15"])

    def test_v13_accepts_actual_github_checkout_trace_format(self):
        s = fake_snapshot()
        s["raw_job_log"] = s["raw_job_log"].replace(
            "2026-10-25T01:35:32Z ref: "+v.PINNED_SHA,
            "2026-10-25T01:35:35.7066869Z   ref: "+v.PINNED_SHA)
        s["raw_job_log"] = s["raw_job_log"].replace(
            "2026-10-25T01:35:36Z git checkout --progress --force "+v.PINNED_SHA,
            "2026-10-25T01:35:36.5999912Z [command]/usr/bin/git checkout --progress --force "+v.PINNED_SHA)
        self.assertEqual("PASS", statuses(s)["V13"])

    def test_malformed_log_json_reports_unverified(self):
        s=fake_snapshot();s["raw_job_log"]="{not valid JSON"
        self.assertEqual("UNVERIFIED", statuses(s)["V17"])


if __name__ == "__main__":
    unittest.main()
