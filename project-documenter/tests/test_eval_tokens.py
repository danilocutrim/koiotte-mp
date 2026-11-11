import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import eval_tokens as et  # noqa: E402


def msg(mid, model, inp, cc, cr, out, role="assistant"):
    return json.dumps({"type": role, "message": {
        "id": mid, "role": role, "model": model,
        "usage": {"input_tokens": inp, "cache_creation_input_tokens": cc,
                  "cache_read_input_tokens": cr, "output_tokens": out}}})


def write_trace(lines):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    f.write("\n".join(lines) + "\n")
    f.close()
    return f.name


class UsageTest(unittest.TestCase):
    def test_sums_per_model(self):
        p = write_trace([msg("a", "opus", 2, 100, 0, 10), msg("b", "sonnet", 3, 0, 500, 20)])
        u = et.usage_from_trace(p)
        self.assertEqual(u["opus"]["output_tokens"], 10)
        self.assertEqual(u["sonnet"]["cache_read_input_tokens"], 500)

    def test_same_message_id_counted_once_using_largest_values(self):
        p = write_trace([msg("a", "opus", 2, 100, 0, 3), msg("a", "opus", 2, 100, 0, 40)])
        u = et.usage_from_trace(p)
        self.assertEqual(u["opus"]["output_tokens"], 40)
        self.assertEqual(u["opus"]["cache_creation_input_tokens"], 100)

    def test_skips_corrupt_lines_and_lines_without_usage(self):
        p = write_trace(["{não é json", json.dumps({"type": "user", "message": {"role": "user"}}),
                         msg("a", "opus", 1, 0, 0, 5)])
        self.assertEqual(et.usage_from_trace(p)["opus"]["output_tokens"], 5)

    def test_user_messages_ignored(self):
        p = write_trace([msg("u", "opus", 9, 9, 9, 9, role="user")])
        self.assertEqual(dict(et.usage_from_trace(p)), {})


class ReportTest(unittest.TestCase):
    def result_json(self, trace_path):
        data = {"cases": [{"name": "c1", "arms": {
            "with": [{"costUsd": 0.2, "tracePath": trace_path}],
            "without": [{"costUsd": 0.3, "tracePath": "/nao/existe/trace.jsonl"}]}}]}
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, f)
        f.close()
        return f.name

    def test_rows_per_arm_with_missing_trace(self):
        t = write_trace([msg("a", "opus", 2, 100, 400, 10), msg("b", "sonnet", 1, 0, 100, 5)])
        rows = et.report(self.result_json(t))
        by_arm = {r["arm"]: r for r in rows}
        self.assertEqual(by_arm["with"]["input"], 3)
        self.assertEqual(by_arm["with"]["cache_write"], 100)
        self.assertEqual(by_arm["with"]["cache_read"], 500)
        self.assertEqual(by_arm["with"]["output"], 15)
        self.assertEqual(by_arm["with"]["cost_usd"], 0.2)
        self.assertIsNone(by_arm["without"]["input"])  # trace ausente: não inventa zero
        self.assertEqual(by_arm["without"]["cost_usd"], 0.3)

    def test_cli_prints_table_and_flags_missing_trace(self):
        t = write_trace([msg("a", "opus", 2, 100, 400, 10)])
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_tokens.py"), self.result_json(t)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("c1", r.stdout)
        self.assertIn("trace ausente", r.stdout)
        self.assertIn("--keep-temp", r.stdout)

    # Medido no trace real: Write de ~590 tokens aparece com output_tokens=16 (snapshot do início do stream)
    def test_cli_marks_output_as_lower_bound_and_points_to_cost(self):
        t = write_trace([msg("a", "opus", 2, 100, 400, 10)])
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_tokens.py"), self.result_json(t)],
                           capture_output=True, text=True)
        self.assertIn("saída (mín.)", r.stdout)
        self.assertIn("piso", r.stdout)
        self.assertIn("US$", r.stdout)

    def test_cli_bad_args_and_unreadable_json(self):
        script = str(ROOT / "scripts" / "eval_tokens.py")
        self.assertEqual(subprocess.run([sys.executable, script], capture_output=True).returncode, 2)
        bad = subprocess.run([sys.executable, script, "/nao/existe.json"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertNotIn("Traceback", bad.stderr)


if __name__ == "__main__":
    unittest.main()
