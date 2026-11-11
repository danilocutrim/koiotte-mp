import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import index_tool as it  # noqa: E402

FLOW = """# Escopo — Fluxo

## Componentes
- order-service

## Fluxos principais
### Criar pedido
1. cliente chama POST /orders

### Cancelar pedido
1. cliente chama DELETE /orders/1

## Infra e deploy
SQS + Lambda
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "flow.md").write_text(FLOW, encoding="utf-8")
        (self.dir / "sequence-criar-pedido.mmd").write_text("sequenceDiagram\n  A->>B: oi\n")


class SectionsTest(Base):
    def test_h2_includes_children(self):
        secs = it.parse_sections(FLOW)
        self.assertIn("Criar pedido", secs["Fluxos principais"])
        self.assertIn("Cancelar pedido", secs["Fluxos principais"])

    def test_h3_key(self):
        secs = it.parse_sections(FLOW)
        self.assertIn("Fluxos principais › Criar pedido", secs)
        self.assertNotIn("Cancelar", secs["Fluxos principais › Criar pedido"])

    def test_hash_stable_and_sensitive(self):
        k = "Fluxos principais › Criar pedido"
        h1 = it.section_hash(FLOW, k)
        self.assertEqual(h1, it.section_hash(FLOW, k))
        self.assertNotEqual(h1, it.section_hash(FLOW.replace("POST /orders", "PUT /orders"), k))
        self.assertEqual(len(h1), 12)

    def test_unrelated_change_keeps_hash(self):
        k = "Fluxos principais › Criar pedido"
        changed = FLOW.replace("SQS + Lambda", "ECS")
        self.assertEqual(it.section_hash(FLOW, k), it.section_hash(changed, k))

    def test_missing_section_raises(self):
        with self.assertRaises(KeyError):
            it.section_hash(FLOW, "Não existe")


class AddCheckTest(Base):
    ORIGIN = "Fluxos principais › Criar pedido"

    def add(self):
        it.add(self.dir, "sequence-criar-pedido.mmd", "sequência", "mermaid", self.ORIGIN, today="2026-10-02")

    def test_add_creates_index_and_check_ok(self):
        self.add()
        idx = (self.dir / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| sequence-criar-pedido.mmd | sequência | mermaid |", idx)
        self.assertIn("2026-10-02", idx)
        self.assertEqual(it.check(self.dir), [("sequence-criar-pedido.mmd", [])])

    def test_add_twice_replaces_row(self):
        self.add()
        self.add()
        rows = [l for l in (self.dir / "INDEX.md").read_text(encoding="utf-8").splitlines() if "sequence-criar" in l]
        self.assertEqual(len(rows), 1)

    def test_stale_when_origin_changes(self):
        self.add()
        flow = self.dir / "flow.md"
        flow.write_text(FLOW.replace("POST /orders", "PUT /orders"), encoding="utf-8")
        self.assertEqual(it.check(self.dir), [("sequence-criar-pedido.mmd", ["desatualizado"])])

    def test_hand_edited(self):
        self.add()
        with open(self.dir / "sequence-criar-pedido.mmd", "a") as f:
            f.write("  B->>A: tchau\n")
        self.assertEqual(it.check(self.dir), [("sequence-criar-pedido.mmd", ["editado-à-mão"])])

    def test_stale_and_edited_both_reported(self):
        self.add()
        with open(self.dir / "sequence-criar-pedido.mmd", "a") as f:
            f.write("x\n")
        (self.dir / "flow.md").write_text(FLOW.replace("POST /orders", "PUT /orders"), encoding="utf-8")
        flags = it.check(self.dir)[0][1]
        self.assertEqual(sorted(flags), ["desatualizado", "editado-à-mão"])

    def test_origin_removed_and_file_missing(self):
        self.add()
        (self.dir / "flow.md").write_text("## Componentes\nx\n", encoding="utf-8")
        (self.dir / "sequence-criar-pedido.mmd").unlink()
        flags = it.check(self.dir)[0][1]
        self.assertEqual(sorted(flags), ["arquivo-ausente", "origem-removida"])

    # Final review, Important 1: diagrams built from several sections
    def test_multi_origin_detects_change_in_any_section(self):
        origin = "Componentes + Infra e deploy"
        it.add(self.dir, "sequence-criar-pedido.mmd", "arquitetura", "drawio", origin, today="2026-10-02")
        self.assertEqual(it.check(self.dir)[0][1], [])
        (self.dir / "flow.md").write_text(FLOW.replace("SQS + Lambda", "ECS"), encoding="utf-8")
        self.assertEqual(it.check(self.dir)[0][1], ["desatualizado"])
        (self.dir / "flow.md").write_text(FLOW.replace("- order-service", "- order-svc"), encoding="utf-8")
        self.assertEqual(it.check(self.dir)[0][1], ["desatualizado"])

    def test_multi_origin_with_missing_part_errors(self):
        with self.assertRaises(ValueError):
            it.add(self.dir, "sequence-criar-pedido.mmd", "arquitetura", "drawio", "Componentes + Fantasma")
        self.assertFalse((self.dir / "INDEX.md").exists())

    # Review Focus 1
    def test_add_unknown_origin_errors_and_leaves_index_untouched(self):
        with self.assertRaises(ValueError):
            it.add(self.dir, "sequence-criar-pedido.mmd", "sequência", "mermaid", "Seção fantasma")
        self.assertFalse((self.dir / "INDEX.md").exists())

    def test_add_missing_diagram_file_errors(self):
        with self.assertRaises(ValueError):
            it.add(self.dir, "nao-existe.mmd", "sequência", "mermaid", self.ORIGIN)

    # Review Focus 3
    def test_pipe_in_field_rejected(self):
        (self.dir / "a|b.mmd").write_text("x")
        with self.assertRaises(ValueError):
            it.add(self.dir, "a|b.mmd", "sequência", "mermaid", self.ORIGIN)
        self.assertFalse((self.dir / "INDEX.md").exists())


class CliTest(Base):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "index_tool.py"), *args],
                              capture_output=True, text=True)

    # Review Focus 2
    def test_check_without_index(self):
        r = self.run_cli("check", str(self.dir))
        self.assertEqual(r.returncode, 0)
        self.assertIn("sem INDEX.md", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_add_then_check_cli(self):
        r = self.run_cli("add", str(self.dir), "sequence-criar-pedido.mmd", "sequência", "mermaid",
                         "Fluxos principais › Criar pedido")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("check", str(self.dir))
        self.assertEqual(r.stdout.strip(), "sequence-criar-pedido.mmd\tok")

    def test_add_error_exit_code(self):
        r = self.run_cli("add", str(self.dir), "sequence-criar-pedido.mmd", "sequência", "mermaid", "Fantasma")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Fantasma", r.stderr)


class RobustnessTest(Base):
    ORIGIN = "Fluxos principais › Criar pedido"

    def add(self):
        it.add(self.dir, "sequence-criar-pedido.mmd", "sequência", "mermaid", self.ORIGIN, today="2026-10-02")

    def test_malformed_index_row_is_flagged_not_a_crash(self):
        self.add()
        idx = self.dir / "INDEX.md"
        idx.write_text(idx.read_text(encoding="utf-8") + "| so-duas | colunas |\n", encoding="utf-8")
        result = it.check(self.dir)
        self.assertEqual(result[0], ("sequence-criar-pedido.mmd", []))
        self.assertEqual(result[1][1], ["linha-inválida"])

    def test_diagram_that_is_a_directory_is_rejected(self):
        (self.dir / "pasta.mmd").mkdir()
        with self.assertRaises(ValueError):
            it.add(self.dir, "pasta.mmd", "sequência", "mermaid", self.ORIGIN)

    def test_non_utf8_flow_is_a_clear_error(self):
        (self.dir / "flow.md").write_bytes(b"## Componentes\n\xff\xfe lixo\n")
        with self.assertRaises(ValueError) as ctx:
            it.add(self.dir, "sequence-criar-pedido.mmd", "sequência", "mermaid", "Componentes")
        self.assertIn("flow.md", str(ctx.exception))

    def test_check_without_flow_reports_flow_missing_not_origin_removed(self):
        self.add()
        (self.dir / "flow.md").unlink()
        flags = it.check(self.dir)[0][1]
        self.assertIn("flow-ausente", flags)
        self.assertNotIn("origem-removida", flags)

    def test_newline_in_field_is_rejected(self):
        with self.assertRaises(ValueError):
            it.add(self.dir, "sequence-criar-pedido.mmd", "sequên\ncia", "mermaid", self.ORIGIN)
        self.assertFalse((self.dir / "INDEX.md").exists())

    def test_headings_inside_code_fences_are_not_sections(self):
        flow = "## Componentes\n```bash\n## falso\n### tambem falso\n```\nresto\n\n## Infra e deploy\nx\n"
        secs = it.parse_sections(flow)
        self.assertNotIn("falso", secs)
        self.assertIn("resto", secs["Componentes"])
        self.assertIn("## falso", secs["Componentes"])

    def test_duplicate_h3_under_same_h2_is_rejected_on_add(self):
        (self.dir / "flow.md").write_text("## Fluxos principais\n### Criar\na\n### Criar\nb\n", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            it.add(self.dir, "sequence-criar-pedido.mmd", "sequência", "mermaid", "Fluxos principais › Criar")
        self.assertIn("duplicado", str(ctx.exception))

    def test_cli_add_with_extra_args_is_a_usage_error(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "index_tool.py"), "add", str(self.dir),
                            "sequence-criar-pedido.mmd", "sequência", "mermaid", self.ORIGIN, "sobra"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.dir / "INDEX.md").exists())

    def test_cli_check_on_flow_missing_prints_flag(self):
        self.add()
        (self.dir / "flow.md").unlink()
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "index_tool.py"), "check", str(self.dir)],
                           capture_output=True, text=True)
        self.assertIn("flow-ausente", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
