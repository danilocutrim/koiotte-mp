import json
import re
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


class ManifestTest(unittest.TestCase):
    def test_plugin_json(self):
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(data["name"], "project-documenter")
        self.assertTrue(data["version"])
        self.assertTrue(data["description"])


class ComponentTest(unittest.TestCase):
    def test_commands_and_agents_have_description(self):
        for folder in ("commands", "agents"):
            for p in (ROOT / folder).glob("*.md"):
                fm = frontmatter(p)
                self.assertIsNotNone(fm, f"{p} sem frontmatter")
                self.assertTrue(fm.get("description"), f"{p} sem description")
                self.assertLessEqual(len(fm["description"]), 400, p)

    def test_agents_declare_name_and_tools(self):
        for p in (ROOT / "agents").glob("*.md"):
            fm = frontmatter(p)
            self.assertEqual(fm.get("name"), p.stem, p)
            self.assertTrue(fm.get("tools"), f"{p} sem tools")

    def test_skills(self):
        for skill in (ROOT / "skills").glob("*/SKILL.md"):
            fm = frontmatter(skill)
            self.assertIsNotNone(fm, f"{skill} sem frontmatter")
            self.assertEqual(fm.get("name"), skill.parent.name, skill)
            self.assertTrue(fm.get("description"), skill)
            self.assertLessEqual(len(fm["description"]), 400, skill)

    def test_skill_references_are_consistent(self):
        for skill in (ROOT / "skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8")
            linked = set(re.findall(r"references/([\w-]+\.md)", text))
            existing = {p.name for p in (skill.parent / "references").glob("*.md")}
            self.assertEqual(linked, existing, f"{skill}: links x arquivos divergem")


EXPECTED = [
    ".claude-plugin/plugin.json",
    "commands/diagram.md",
    "agents/project-analyst.md",
    "skills/mermaid/SKILL.md",
    "skills/mermaid/references/sequence.md",
    "skills/mermaid/references/flow.md",
    "skills/mermaid/references/architecture.md",
    "skills/drawio/SKILL.md",
    "skills/drawio/references/architecture.md",
    "skills/drawio/references/infra-aws.md",
    "scripts/validate_drawio.py",
    "scripts/index_tool.py",
    "skills/drawio/references/sample.drawio",
    "skills/drawio/references/request-path.md",
    "skills/drawio/references/request-path-sample.drawio",
]


class CompletenessTest(unittest.TestCase):
    def test_expected_components_exist(self):
        missing = [p for p in EXPECTED if not (ROOT / p).exists()]
        self.assertEqual(missing, [])

    # Final review, Important 2: never lose the approved flow.md
    def test_command_backs_up_flow_before_analyst(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        self.assertIn("flow.md.prev", text)
        self.assertLess(text.index("flow.md.prev"), text.index("## 3. Gate"))

    # Final review, Important 1: multi-section origins are documented
    def test_command_documents_multi_section_origin(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        self.assertIn("Componentes + Integrações externas", text)
        self.assertIn("Infra e deploy + Componentes", text)

    # Final review, Minor 3 (re-graded: Review Focus 5 path): agent never drops headings
    def test_agent_keeps_all_headings_for_empty_projects(self):
        text = (ROOT / "agents" / "project-analyst.md").read_text(encoding="utf-8")
        self.assertNotIn("só com **Visão geral**", text)
        self.assertIn("Nada encontrado.", text)

    def test_command_handles_flow_without_components(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        self.assertIn("Nada encontrado.", text)

    # Eval pilot: analyst did not fire on natural prompts ("documente como X funciona")
    def test_agent_description_has_trigger_phrases(self):
        fm = frontmatter(ROOT / "agents" / "project-analyst.md")
        desc = fm["description"]
        self.assertIn("Use quando", desc)
        for phrase in ("documentar", "entender", "como funciona", "fluxo específico"):
            self.assertIn(phrase, desc)
        self.assertLessEqual(len(desc), 400)

    # Eval pilot (monorepo): citations must be resolvable from the repo root
    def test_agent_cites_paths_with_scope_prefix(self):
        text = (ROOT / "agents" / "project-analyst.md").read_text(encoding="utf-8")
        self.assertIn("<ESCOPO>/arquivo:linha", text)

    # Diagrama real saiu desorganizado: a skill precisa ensinar roteamento, tamanho e o lint
    def test_drawio_skill_teaches_layout_rules(self):
        skill = (ROOT / "skills" / "drawio" / "SKILL.md").read_text(encoding="utf-8")
        arch = (ROOT / "skills" / "drawio" / "references" / "architecture.md").read_text(encoding="utf-8")
        for needle in ("edgeStyle=orthogonalEdgeStyle", "tooltip", "3 linhas", "atravessa", "aviso"):
            self.assertIn(needle, skill, f"SKILL.md sem '{needle}'")
        self.assertIn("edgeStyle=orthogonalEdgeStyle", arch)
        self.assertIn("minimizar cruzamentos", arch)

    def test_sample_drawio_follows_the_edge_rule(self):
        sample = (ROOT / "skills" / "drawio" / "references" / "sample.drawio").read_text(encoding="utf-8")
        self.assertIn("edgeStyle=orthogonalEdgeStyle", sample)

    # Menor privilégio: os evals só podem rodar o validador, nunca "python3" genérico
    def test_eval_cases_do_not_grant_generic_shell(self):
        for prompt in (ROOT / "evals").glob("*/prompt.md"):
            text = prompt.read_text(encoding="utf-8")
            self.assertNotIn("Bash(python3:*)", text, prompt)
            self.assertNotIn("Bash(*)", text, prompt)
            for pattern in re.findall(r'Bash\(([^)]*)\)', text):
                self.assertIn("validate_drawio.py", pattern, f"{prompt}: Bash fora do validador: {pattern}")

    # Item 2: a skill passa a ensinar camadas, corredores, contêineres reais e o ciclo de renderização
    def _drawio_texts(self):
        base = ROOT / "skills" / "drawio"
        return {
            "skill": (base / "SKILL.md").read_text(encoding="utf-8"),
            "layout": (base / "references" / "layout.md").read_text(encoding="utf-8"),
            "arch": (base / "references" / "architecture.md").read_text(encoding="utf-8"),
            "infra": (base / "references" / "infra-aws.md").read_text(encoding="utf-8"),
        }

    def test_drawio_skill_teaches_tiers_corridors_and_containers(self):
        x = self._drawio_texts()
        for needle in ("camadas", "corredor", "hub", "swimlane", "startSize", "coordenadas relativas",
                       'parent="1"', "orthogonalLoop=1", "jettySize=auto", "rótulo próprio", "grade de 10"):
            self.assertIn(needle, x["skill"] + x["layout"], f"faltou '{needle}'")
        self.assertNotIn("coordenadas absolutas na página", x["skill"])

    def test_drawio_layout_reference_has_a_procedure(self):
        layout = self._drawio_texts()["layout"]
        for needle in ("baricentro", "hub", "rota", "sobrepõem", "horizontal primeiro", "agregue"):
            self.assertIn(needle, layout, f"layout.md sem '{needle}'")

    def test_drawio_skill_closes_the_loop_with_a_render(self):
        skill = self._drawio_texts()["skill"]
        for needle in ("drawio -x -f png", "Read", "command -v drawio", "não foi renderizado",
                       "route_check.py", "passa por dentro"):
            self.assertIn(needle, skill, f"SKILL.md sem '{needle}'")

    def test_drawio_aws_reference_keeps_regional_services_out_of_the_vpc(self):
        infra = self._drawio_texts()["infra"]
        for needle in ("CloudWatch", "CloudTrail", "fora da VPC"):
            self.assertIn(needle, infra)

    # Minors deferidos da revisão final
    def test_command_defines_fixed_file_slugs(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        for slug in ("sequence-", "flow-", "architecture-", "infra-", "request-"):
            self.assertIn(slug, text, f"slug '{slug}' não definido")
        self.assertIn("sem espaços", text)

    def test_drawio_sample_ships_inside_the_skill(self):
        skill = (ROOT / "skills" / "drawio" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue((ROOT / "skills" / "drawio" / "references" / "sample.drawio").exists())
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/drawio/references/sample.drawio", skill)
        self.assertNotIn("tests/fixtures/sample.drawio", skill)

    # Caminho da requisição: colunas fixas, portas explícitas, um destaque, molde validado dentro da skill
    def test_drawio_request_path_reference_teaches_columns(self):
        ref = (ROOT / "skills" / "drawio" / "references" / "request-path.md").read_text(encoding="utf-8")
        for needle in ("coluna", "barramento", "entryX", "calha", "monoespaçado", "tracejada", "um destaque",
                       "${CLAUDE_PLUGIN_ROOT}/skills/drawio/references/request-path-sample.drawio"):
            self.assertIn(needle, ref, f"request-path.md sem '{needle}'")
        skill = (ROOT / "skills" / "drawio" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("request-path-sample.drawio", skill)

    def test_request_path_sample_passes_the_validator_without_warnings(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_drawio import validate, lint_layout
        sample = ROOT / "skills" / "drawio" / "references" / "request-path-sample.drawio"
        self.assertEqual(validate(sample), [])
        self.assertEqual(lint_layout(sample), ([], []))

    def test_command_offers_request_path_only_as_drawio(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        self.assertIn("| caminho da requisição | Fluxos principais (um `###`) + Componentes | drawio |", text)
        self.assertIn("Fluxos principais › <nome do fluxo> + Componentes", text)

    def test_overwrite_prompt_checks_for_hand_edits_first(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        step5 = text[text.index("## 5. Geração"):text.index("## 6. Índice")]
        self.assertIn("index_tool.py", step5)
        self.assertIn("editado-à-mão", step5)

    def test_mermaid_flow_reference_reads_only_the_registered_section(self):
        flow = (ROOT / "skills" / "mermaid" / "references" / "flow.md").read_text(encoding="utf-8")
        self.assertNotIn("Visão geral", flow.split("## Mapeamento")[0])

    # Regras do entrevistador de evals: runs>=3, grader de resultado em todo caso, ao menos um caso negativo
    def test_every_eval_case_follows_the_suite_rules(self):
        cases = sorted((ROOT / "evals").glob("*/prompt.md"))
        self.assertGreaterEqual(len(cases), 16)
        for prompt in cases:
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("runs: 3", text, prompt)
            self.assertIn("timeout_seconds:", text, prompt)
            self.assertIn("allowed_tools:", text, prompt)
            types = [re.search(r"^type:\s*(\w+)", g.read_text(encoding="utf-8"), re.M).group(1)
                     for g in (prompt.parent / "graders").glob("*.md")]
            self.assertTrue(any(ty != "tool_used" for ty in types), f"{prompt}: só graders de trajetória")

    def test_mermaid_eval_suite_exists_with_a_negative_case(self):
        cases = sorted((ROOT / "evals").glob("mermaid-*/prompt.md"))
        self.assertGreaterEqual(len(cases), 5)
        self.assertTrue(any("neg" in c.parent.name for c in cases))
        for c in cases:
            self.assertNotIn("Bash", c.read_text(encoding="utf-8"), f"{c}: mermaid não precisa de shell")

    # Os próprios graders são testados com saídas reais do piloto (graders errados punem o comportamento certo)
    @staticmethod
    def _grader(case, name):
        text = (ROOT / "evals" / case / "graders" / f"{name}.md").read_text(encoding="utf-8")
        _, fm, body = text.split("---", 2)
        flags = re.I if re.search(r"^flags:\s*\w*i", fm, re.M) else 0
        return re.compile(body.strip(), flags)

    def test_mermaid_flow_grader_accepts_a_leading_comment_and_graph_keyword(self):
        rx = self._grader("mermaid-02-flowchart-big", "is-flowchart")
        self.assertTrue(rx.search("%% parte 1/3\nflowchart TD\n  a --> b"))
        self.assertTrue(rx.search("flowchart TD\n  a --> b"))
        self.assertTrue(rx.search("graph LR\n  a --> b"))
        self.assertFalse(rx.search("sequenceDiagram\n  A->>B: oi"))

    def test_mermaid_size_is_judged_by_the_rubric_not_by_a_brittle_regex(self):
        g = ROOT / "evals" / "mermaid-02-flowchart-big" / "graders"
        self.assertFalse((g / "handles-size.md").exists())  # a redação do encadeamento varia entre runs
        rubric = (g / "node-limit-and-decisions.md").read_text(encoding="utf-8")
        self.assertIn("type: llm", rubric)
        self.assertIn("15 nós", rubric)

    def test_mermaid_login_order_grader_is_case_insensitive(self):
        rx = self._grader("mermaid-01-sequence-login", "keeps-message-order")
        self.assertTrue(rx.search("Cliente->>API: POST /login\nAPI-->>Cliente: Token"))
        self.assertTrue(rx.search("client->>api: POST /login\napi-->>client: token"))
        self.assertFalse(rx.search("API-->>Cliente: token\nCliente->>API: POST /login"))

    def test_mermaid_validation_honesty_uses_the_judge_not_a_negation_blind_regex(self):
        g = (ROOT / "evals" / "mermaid-03-honest-validation" / "graders")
        self.assertFalse((g / "no-false-validation-claim.md").exists())
        rubric = (g / "does-not-claim-validated.md").read_text(encoding="utf-8")
        self.assertIn("type: llm", rubric)
        self.assertIn("não afirma", rubric)

    # O plugin é agnóstico: nada de nomes de projetos privados no repositório
    def test_repository_has_no_private_project_names(self):
        forbidden = ["koi" + "otte"]  # montado em partes para este teste não conter o termo
        skip_dirs = {".git", ".claude", "__pycache__", ".superpowers"}
        offenders = []
        for path in ROOT.rglob("*"):
            rel = path.relative_to(ROOT)
            if set(rel.parts) & skip_dirs or rel.parts[:2] == ("evals", "results") or not path.is_file():
                continue
            haystack = (str(rel) + "\n" + path.read_bytes().decode("utf-8", "ignore")).lower()
            offenders += [str(rel) for word in forbidden if word in haystack]
        self.assertEqual(offenders, [])

    def test_command_references_real_scripts_and_agent(self):
        text = (ROOT / "commands" / "diagram.md").read_text(encoding="utf-8")
        for script in re.findall(r"scripts/([\w]+\.py)", text):
            self.assertTrue((ROOT / "scripts" / script).exists(), script)
        self.assertIn("project-analyst", text)


if __name__ == "__main__":
    unittest.main()
