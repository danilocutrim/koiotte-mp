import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import eval_lint as el  # noqa: E402

GOOD = (ROOT / "skills" / "drawio" / "references" / "sample.drawio").read_text(encoding="utf-8")
MESSY = (ROOT / "tests" / "fixtures" / "crowded-architecture.drawio").read_text(encoding="utf-8")


def make_run(base, name, files):
    """Cria <base>/<name>/{out/trace.jsonl, sealed/home/cwd/<files>} e devolve o tracePath."""
    root = Path(base) / name
    (root / "out").mkdir(parents=True)
    (root / "out" / "trace.jsonl").write_text("{}\n")
    for rel, content in files.items():
        f = root / "sealed" / "home" / "cwd" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    return str(root / "out" / "trace.jsonl")


def result_json(runs):
    """runs: list of (case, arm, tracePath)."""
    cases = {}
    for case, arm, trace in runs:
        cases.setdefault(case, {"name": case, "arms": {}})["arms"].setdefault(arm, []).append({"tracePath": trace})
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"cases": list(cases.values())}, f)
    f.close()
    return f.name


class LintRunsTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()

    def test_clean_file_has_no_findings(self):
        t = make_run(self.base, "a", {"docs/x.drawio": GOOD})
        rows = el.lint_runs(result_json([("c1", "with", t)]))
        self.assertEqual(rows[0]["files"], 1)
        self.assertEqual((rows[0]["errors"], rows[0]["warnings"]), (0, 0))
        self.assertEqual(rows[0]["status"], "ok")

    def test_messy_file_counts_errors_and_warnings(self):
        t = make_run(self.base, "a", {"docs/x.drawio": MESSY})
        row = el.lint_runs(result_json([("c1", "without", t)]))[0]
        self.assertGreaterEqual(row["errors"], 3)
        self.assertGreaterEqual(row["warnings"], 3)

    def test_run_without_drawio_is_flagged_not_zero(self):
        t = make_run(self.base, "a", {"docs/x.md": "# nada"})
        row = el.lint_runs(result_json([("c1", "with", t)]))[0]
        self.assertEqual(row["files"], 0)
        self.assertEqual(row["status"], "sem .drawio")
        self.assertIsNone(row["errors"])

    def test_missing_trace_dir_is_flagged(self):
        row = el.lint_runs(result_json([("c1", "with", "/nao/existe/out/trace.jsonl")]))[0]
        self.assertEqual(row["status"], "run ausente")
        self.assertIsNone(row["errors"])

    def test_structurally_invalid_file_counts_as_error(self):
        t = make_run(self.base, "a", {"docs/x.drawio": "<foo/>"})
        row = el.lint_runs(result_json([("c1", "with", t)]))[0]
        self.assertGreaterEqual(row["errors"], 1)

    def test_sealed_directory_is_made_readable(self):
        t = make_run(self.base, "a", {"docs/x.drawio": GOOD})
        sealed = Path(t).parent.parent / "sealed"
        sealed.chmod(0o000)
        try:
            row = el.lint_runs(result_json([("c1", "with", t)]))[0]
            self.assertEqual(row["files"], 1)
        finally:
            sealed.chmod(0o700)

    def test_summary_per_arm(self):
        good = make_run(self.base, "g", {"d.drawio": GOOD})
        bad = make_run(self.base, "b", {"d.drawio": MESSY})
        rows = el.lint_runs(result_json([("c1", "with", good), ("c1", "with", good), ("c1", "without", bad)]))
        s = el.summarize(rows)
        self.assertEqual(s["with"]["runs"], 2)
        self.assertEqual(s["with"]["clean"], 2)
        self.assertEqual(s["without"]["clean"], 0)

    def test_cli_prints_table_and_summary(self):
        good = make_run(self.base, "g", {"d.drawio": GOOD})
        bad = make_run(self.base, "b", {"d.drawio": MESSY})
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_lint.py"),
                            result_json([("c1", "with", good), ("c1", "without", bad)])],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("c1", r.stdout)
        self.assertIn("sem erro de layout", r.stdout)
        self.assertIn("--keep-temp", r.stdout)

    # Métricas do que a skill muda (rótulos, grupos, tooltips), além de erros de layout
    def test_metrics_of_sample(self):
        m = el.metrics(ROOT / "skills" / "drawio" / "references" / "sample.drawio")
        self.assertEqual((m["edges"], m["labeled_edges"], m["groups"], m["tooltips"]), (2, 2, 1, 1))

    def test_rows_carry_metrics(self):
        t = make_run(self.base, "a", {"docs/x.drawio": GOOD})
        row = el.lint_runs(result_json([("c1", "with", t)]))[0]
        self.assertEqual((row["edges"], row["labeled_edges"], row["groups"], row["tooltips"]), (2, 2, 1, 1))

    def test_unlabeled_edges_are_counted(self):
        unlabeled = GOOD.replace(' value="HTTPS"', ' value=""').replace(' value="evento"', "")
        t = make_run(self.base, "a", {"docs/x.drawio": unlabeled})
        row = el.lint_runs(result_json([("c1", "without", t)]))[0]
        self.assertEqual((row["edges"], row["labeled_edges"]), (2, 0))

    def test_summary_has_label_ratio(self):
        a = make_run(self.base, "a", {"d.drawio": GOOD})
        s = el.summarize(el.lint_runs(result_json([("c1", "with", a)])))
        self.assertEqual(s["with"]["edges"], 2)
        self.assertEqual(s["with"]["labeled_edges"], 2)

    def test_save_copies_each_runs_drawio(self):
        a = make_run(self.base, "a", {"docs/x.drawio": GOOD})
        out = Path(tempfile.mkdtemp())
        el.lint_runs(result_json([("c1", "with", a)]), save_dir=out)
        self.assertTrue((out / "c1-with-1.drawio").exists())
        self.assertEqual((out / "c1-with-1.drawio").read_text(encoding="utf-8"), GOOD)

    def test_cli_save_flag_and_metrics_columns(self):
        a = make_run(self.base, "a", {"docs/x.drawio": GOOD})
        out = Path(tempfile.mkdtemp())
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_lint.py"),
                            result_json([("c1", "with", a)]), "--save", str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((out / "c1-with-1.drawio").exists())
        self.assertIn("setas rotuladas", r.stdout)

    # Rota exata (renderizada) por run: injetada para testar sem o CLI do draw.io
    def test_route_checker_adds_exact_route_metrics(self):
        a = make_run(self.base, "a", {"d.drawio": GOOD})
        fake = lambda path: {"through": ["x passa por dentro de y"], "crossings": [("e1", "e2"), ("e1", "e3")]}
        row = el.lint_runs(result_json([("c1", "with", a)]), route_checker=fake)[0]
        self.assertEqual((row["through"], row["crossings"]), (1, 2))

    def test_route_checker_none_means_not_rendered_not_zero(self):
        a = make_run(self.base, "a", {"d.drawio": GOOD})
        row = el.lint_runs(result_json([("c1", "with", a)]), route_checker=lambda path: None)[0]
        self.assertIsNone(row["through"])
        self.assertIsNone(row["crossings"])

    def test_without_checker_route_metrics_are_absent(self):
        a = make_run(self.base, "a", {"d.drawio": GOOD})
        row = el.lint_runs(result_json([("c1", "with", a)]))[0]
        self.assertIsNone(row["through"])

    def test_summary_counts_runs_without_arrows_through_nodes(self):
        a = make_run(self.base, "a", {"d.drawio": GOOD})
        b = make_run(self.base, "b", {"d.drawio": GOOD})
        calls = iter([{"through": [], "crossings": [("e1", "e2")]}, {"through": ["x"], "crossings": []}])
        rows = el.lint_runs(result_json([("c1", "with", a), ("c1", "with", b)]), route_checker=lambda p: next(calls))
        s = el.summarize(rows)["with"]
        self.assertEqual((s["rendered"], s["no_through"], s["through"], s["crossings"]), (2, 1, 1, 1))

    def test_cli_render_flag_without_cli_reports_not_rendered(self):
        import os
        a = make_run(self.base, "a", {"d.drawio": GOOD})
        env = dict(os.environ, PATH="/nonexistent")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_lint.py"),
                            result_json([("c1", "with", a)]), "--render"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("não renderizado", r.stdout)

    def test_cli_bad_args_and_unreadable_json(self):
        script = str(ROOT / "scripts" / "eval_lint.py")
        self.assertEqual(subprocess.run([sys.executable, script], capture_output=True).returncode, 2)
        bad = subprocess.run([sys.executable, script, "/nao/existe.json"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertNotIn("Traceback", bad.stderr)


if __name__ == "__main__":
    unittest.main()
