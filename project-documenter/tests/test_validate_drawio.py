import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from validate_drawio import validate, lint_layout  # noqa: E402

GOOD = """<mxfile><diagram name="p1"><mxGraphModel><root>
<mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="a" value="A" vertex="1" parent="1"><mxGeometry x="0" y="0" width="80" height="40" as="geometry"/></mxCell>
<mxCell id="b" value="B" vertex="1" parent="1"><mxGeometry x="200" y="0" width="80" height="40" as="geometry"/></mxCell>
<mxCell id="e1" edge="1" source="a" target="b" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>"""


def write(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".drawio", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


class ValidateTest(unittest.TestCase):
    def test_valid_file(self):
        self.assertEqual(validate(write(GOOD)), [])

    def test_not_xml(self):
        errs = validate(write("isto não é xml"))
        self.assertEqual(len(errs), 1)
        self.assertIn("XML mal formado", errs[0])

    def test_empty_file(self):
        errs = validate(write(""))
        self.assertIn("XML mal formado", errs[0])

    def test_wrong_root(self):
        errs = validate(write("<foo/>"))
        self.assertIn("raiz deve ser <mxfile>", errs)

    def test_duplicate_id(self):
        errs = validate(write(GOOD.replace('id="b"', 'id="a"', 1).replace('target="b"', 'target="a"')))
        self.assertTrue(any("id duplicado: a" in e for e in errs))

    def test_edge_to_missing_node(self):
        errs = validate(write(GOOD.replace('target="b"', 'target="zzz"')))
        self.assertTrue(any("target inválido: zzz" in e for e in errs))

    def test_same_id_in_different_pages_is_ok(self):
        two = GOOD.replace("</mxfile>", GOOD[GOOD.index("<diagram"):])
        self.assertEqual(validate(write(two)), [])

    def test_canonical_sample_is_valid(self):
        sample = ROOT / "skills" / "drawio" / "references" / "sample.drawio"
        self.assertEqual(validate(sample), [])

    def test_cli_exit_codes(self):
        script = str(ROOT / "scripts" / "validate_drawio.py")
        ok = subprocess.run([sys.executable, script, write(GOOD)], capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "OK"))
        bad = subprocess.run([sys.executable, script, write("<foo/>")], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)


NODE_STYLE = "rounded=1;whiteSpace=wrap;html=1;"


def drawio(nodes, edges):
    """nodes: (id, label, x, y, w, h[, parent]); edges: (id, src, tgt[, style[, waypoints]])."""
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for n in nodes:
        nid, label, x, y, w, h = n[:6]
        parent = n[6] if len(n) > 6 else "1"
        cells.append(f'<mxCell id="{nid}" value="{label}" style="{NODE_STYLE}" vertex="1" parent="{parent}">'
                     f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    for e in edges:
        eid, src, tgt = e[:3]
        eparent = e[5] if len(e) > 5 else "1"
        style = e[3] if len(e) > 3 else "endArrow=classic;html=1;"
        way = ""
        if len(e) > 4 and e[4]:
            pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in e[4])
            way = f'<Array as="points">{pts}</Array>'
        cells.append(f'<mxCell id="{eid}" style="{style}" edge="1" parent="{eparent}" source="{src}" target="{tgt}">'
                     f'<mxGeometry relative="1" as="geometry">{way}</mxGeometry></mxCell>')
    return ('<mxfile><diagram name="t"><mxGraphModel><root>' + "".join(cells) +
            '</root></mxGraphModel></diagram></mxfile>')


ROW = [("A", "Alfa", 0, 0, 100, 60), ("B", "Beta", 200, 0, 100, 60), ("C", "Gama", 400, 0, 100, 60)]


class LintTest(unittest.TestCase):
    def lint(self, nodes, edges):
        return lint_layout(write(drawio(nodes, edges)))

    def test_straight_edge_through_third_node_is_error(self):
        errors, _ = self.lint(ROW, [("e", "A", "C")])
        self.assertEqual(len(errors), 1)
        self.assertIn("atravessa", errors[0])
        self.assertIn("Beta", errors[0])

    def test_edge_that_goes_around_is_ok(self):
        nodes = [ROW[0], ("B", "Beta", 200, 150, 100, 60), ROW[2]]
        self.assertEqual(self.lint(nodes, [("e", "A", "C")]), ([], []))

    def test_edge_with_waypoints_is_not_checked(self):
        errors, _ = self.lint(ROW, [("e", "A", "C", "endArrow=classic;", [(250, -80)])])
        self.assertEqual(errors, [])

    def test_orthogonal_edge_not_aligned_is_skipped(self):
        nodes = [("A", "Alfa", 0, 0, 100, 60), ("B", "Beta", 200, 20, 100, 60), ("C", "Gama", 400, 200, 100, 60)]
        errors, _ = self.lint(nodes, [("e", "A", "C", "edgeStyle=orthogonalEdgeStyle;")])
        self.assertEqual(errors, [])

    def test_orthogonal_edge_aligned_through_node_is_error(self):
        errors, _ = self.lint(ROW, [("e", "A", "C", "edgeStyle=orthogonalEdgeStyle;")])
        self.assertEqual(len(errors), 1)

    def test_group_container_is_not_a_third_node(self):
        group = ("G", "Grupo", -20, -20, 560, 100)
        errors, _ = self.lint([group] + ROW[:2], [("e", "A", "B")])
        self.assertEqual(errors, [])

    def test_child_coordinates_are_resolved_through_parent(self):
        nodes = [("G", "Grupo", 150, -50, 200, 200), ("A", "Alfa", 0, 0, 100, 60),
                 ("B", "Beta", 50, 50, 100, 60, "G"),  # absoluto: (200, 0)
                 ("C", "Gama", 500, 0, 100, 60)]
        errors, _ = self.lint(nodes, [("e", "A", "C")])
        self.assertEqual(len(errors), 1)
        self.assertIn("Beta", errors[0])

    def test_label_that_does_not_fit_warns(self):
        nodes = [("A", "EventStreamVerticle + StreamHandler + EventBusPublisher", 0, 0, 120, 60)]
        _, warnings = self.lint(nodes, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("não cabe", warnings[0])

    def test_short_label_does_not_warn(self):
        self.assertEqual(self.lint([("A", "API", 0, 0, 120, 60)], []), ([], []))

    def test_html_entities_count_as_one_character(self):
        label = "&amp;quot;" * 10  # vira &quot; no atributo: 10 aspas, não 60 caracteres
        self.assertEqual(self.lint([("A", label, 0, 0, 120, 60)], []), ([], []))

    # Seta com porta explícita (exitX/entryX) sai e chega na borda, não no centro
    PORTS = "edgeStyle=orthogonalEdgeStyle;html=1;exitX=0.1;exitY=1;entryX=0.1;entryY=0;"

    def test_explicit_ports_define_where_the_route_starts_and_ends(self):
        nodes = [("A", "Alfa", 0, 0, 100, 60), ("C", "Gama", 200, 100, 100, 60),
                 ("W", "Faixa larga", 0, 200, 500, 40)]
        errors, warnings = self.lint(nodes, [("e", "A", "W", self.PORTS.replace("exitX=0.1", "exitX=0.5"))])
        self.assertEqual(errors, [])
        self.assertFalse(any("Gama" in w for w in warnings), warnings)

    def test_children_of_the_source_or_target_are_not_obstacles(self):
        nodes = [("G", "Faixa", 0, 0, 400, 60), ("N", "nota", 150, 10, 200, 40, "G"),
                 ("D", "Destino", 150, 120, 100, 40)]
        style = "edgeStyle=orthogonalEdgeStyle;html=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;"
        errors, warnings = self.lint(nodes, [("e", "G", "D", style)])
        self.assertEqual(errors, [])
        self.assertFalse(any("nota" in w for w in warnings), warnings)

    def test_cli_layout_error_exits_1(self):
        script = str(ROOT / "scripts" / "validate_drawio.py")
        r = subprocess.run([sys.executable, script, write(drawio(ROW, [("e", "A", "C")]))],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("atravessa", r.stdout)

    def test_cli_warning_only_exits_0_and_prints_ok(self):
        script = str(ROOT / "scripts" / "validate_drawio.py")
        nodes = [("A", "EventStreamVerticle + StreamHandler + EventBusPublisher", 0, 0, 120, 60)]
        r = subprocess.run([sys.executable, script, write(drawio(nodes, []))], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("aviso:", r.stdout)
        self.assertTrue(r.stdout.strip().endswith("OK"))

    def test_canonical_sample_has_clean_layout(self):
        self.assertEqual(lint_layout(ROOT / "skills" / "drawio" / "references" / "sample.drawio"), ([], []))

    # Regressão: diagrama real que o draw.io mostrou desorganizado (setas atravessando caixas)
    def test_real_messy_diagram_is_rejected(self):
        errors, warnings = lint_layout(ROOT / "tests" / "fixtures" / "crowded-architecture.drawio")
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("Console de operação" in e and "Control Plane" in e for e in errors))
        self.assertTrue(any("EventStreamVerticle" in w for w in warnings))

    def test_unparsable_file_has_no_layout_findings(self):
        self.assertEqual(lint_layout(write("isto não é xml")), ([], []))


ORTHO = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"


class RouteAndStructureLintTest(unittest.TestCase):
    def lint(self, nodes, edges):
        return lint_layout(write(drawio(nodes, edges)))

    # --- rota ortogonal provável atravessando nó (o defeito que o PNG mostrou) ---
    def test_one_blocked_l_route_warns(self):
        nodes = [("A", "Alfa", 0, 200, 100, 60), ("B", "Beta", 300, 200, 100, 60), ("C", "Gama", 400, 0, 100, 60)]
        errors, warnings = self.lint(nodes, [("e", "A", "C", ORTHO)])
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("rota", warnings[0])
        self.assertIn("Beta", warnings[0])

    def test_both_l_routes_blocked_is_only_a_warning(self):
        # o draw.io pode contornar com rota de 3 segmentos (V-H-V), então não dá para chamar de erro
        nodes = [("A", "Alfa", 0, 200, 100, 60), ("B", "Beta", 300, 200, 100, 60), ("C", "Gama", 400, 0, 100, 60),
                 ("D", "Dd", 20, 100, 60, 40)]
        errors, warnings = self.lint(nodes, [("e", "A", "C", ORTHO)])
        self.assertEqual(errors, [])
        self.assertTrue(any("nenhuma rota ortogonal simples" in w for w in warnings))

    def test_free_l_route_is_clean(self):
        nodes = [("A", "Alfa", 0, 200, 100, 60), ("B", "Beta", 300, 400, 100, 60), ("C", "Gama", 400, 0, 100, 60)]
        self.assertEqual(self.lint(nodes, [("e", "A", "C", ORTHO)]), ([], []))

    def test_edge_with_waypoints_skips_route_check(self):
        nodes = [("A", "Alfa", 0, 200, 100, 60), ("B", "Beta", 300, 200, 100, 60), ("C", "Gama", 400, 0, 100, 60)]
        self.assertEqual(self.lint(nodes, [("e", "A", "C", ORTHO, [(50, 30)])]), ([], []))


    # Rota prevista a partir do padrão observado do draw.io: sobreposição horizontal => sai na vertical
    def test_prediction_uses_vertical_exit_when_boxes_overlap_horizontally(self):
        nodes = [("A", "Alfa", 100, 0, 100, 60), ("C", "Gama", 150, 300, 100, 60),
                 ("D", "Dd", 180, 100, 40, 40)]  # bloqueia a rota H-V, que o draw.io não toma aqui
        self.assertEqual(self.lint(nodes, [("e", "A", "C", ORTHO)]), ([], []))

    def test_prediction_flags_vertical_exit_that_hits_a_node(self):
        nodes = [("A", "Alfa", 100, 0, 100, 60), ("C", "Gama", 150, 300, 100, 60),
                 ("D", "Dd", 130, 100, 40, 40)]  # no caminho da saída vertical
        errors, warnings = self.lint(nodes, [("e", "A", "C", ORTHO)])
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("Dd", warnings[0])

    def test_disjoint_boxes_prediction_is_horizontal_first(self):
        nodes = [("A", "Alfa", 0, 200, 100, 60), ("C", "Gama", 400, 0, 100, 60),
                 ("D", "Dd", 440, 100, 40, 40)]  # só bloqueia a rota V-H (vertical em x=50? não: em x=450)
        # V-H passaria por x=50 e depois y=30; H-V passa por y=230 e depois x=450 (D está em x 440..480, y 100..140)
        _, warnings = self.lint(nodes, [("e", "A", "C", ORTHO)])
        self.assertEqual(len(warnings), 1)
        self.assertIn("Dd", warnings[0])

    # --- rótulos repetidos saindo do mesmo nó ---
    def test_same_label_from_same_source_warns(self):
        nodes = [("H", "Hub", 0, 100, 100, 60), ("A", "A", 300, 0, 100, 60), ("B", "B", 300, 100, 100, 60),
                 ("C", "C", 300, 200, 100, 60)]
        edges = [("e1", "H", "A", "html=1;"), ("e2", "H", "B", "html=1;"), ("e3", "H", "C", "html=1;")]
        xml = drawio(nodes, edges).replace('id="e1"', 'id="e1" value="Route"').replace(
            'id="e2"', 'id="e2" value="Route"').replace('id="e3"', 'id="e3" value="Route"')
        _, warnings = lint_layout(write(xml))
        self.assertEqual(len(warnings), 1)
        self.assertIn("Route", warnings[0])
        self.assertIn("3", warnings[0])

    def test_same_label_from_different_sources_is_fine(self):
        nodes = [("H", "Hub", 200, 100, 100, 60), ("A", "A", 0, 0, 100, 60), ("B", "B", 0, 200, 100, 60)]
        xml = drawio(nodes, [("e1", "A", "H", "html=1;"), ("e2", "B", "H", "html=1;")]).replace(
            'id="e1"', 'id="e1" value="HTTPS"').replace('id="e2"', 'id="e2" value="HTTPS"')
        self.assertEqual(lint_layout(write(xml)), ([], []))

    # --- contêiner de verdade: filhos com parent e arestas entre contêineres em parent=1 ---
    def test_node_inside_group_area_without_parent_warns(self):
        nodes = [("G", "Grupo", 0, 0, 400, 300), ("A", "Alfa", 50, 50, 100, 60)]
        _, warnings = self.lint(nodes, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("não é filho", warnings[0])

    def test_real_child_of_group_is_clean(self):
        nodes = [("G", "Grupo", 0, 0, 400, 300), ("A", "Alfa", 50, 50, 100, 60, "G")]
        self.assertEqual(self.lint(nodes, []), ([], []))

    def test_edge_between_containers_must_be_at_root(self):
        nodes = [("G1", "Grupo 1", 0, 0, 300, 200), ("G2", "Grupo 2", 500, 0, 300, 200),
                 ("A", "Alfa", 50, 50, 100, 60, "G1"), ("B", "Beta", 50, 50, 100, 60, "G2")]
        _, warnings = self.lint(nodes, [("e", "A", "B", "html=1;", None, "G1")])
        self.assertTrue(any("parent=\"1\"" in w for w in warnings))
        _, ok = self.lint(nodes, [("e", "A", "B", "html=1;")])
        self.assertFalse(any("parent=\"1\"" in w for w in ok))

    # --- grade de 10 ---
    def test_off_grid_nodes_warn_once(self):
        nodes = [("A", "Alfa", 43, 20, 100, 60), ("B", "Beta", 200, 27, 100, 60)]
        _, warnings = self.lint(nodes, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("grade de 10", warnings[0])
        self.assertIn("2", warnings[0])


    # Regressão do falso positivo visto no PNG: o draw.io contornou os nós, o linter não pode gritar erro
    def test_shop_tiers_diagram_has_no_route_errors(self):
        errors, _ = lint_layout(ROOT / "tests" / "fixtures" / "shop-tiers-skill.drawio")
        self.assertEqual(errors, [])

    # --- regressão: o par real avaliado no draw.io ---
    def test_shop_with_skill_has_probable_routes_through_nodes(self):
        errors, warnings = lint_layout(ROOT / "tests" / "fixtures" / "shop-with-skill.drawio")
        routes = [w for w in warnings + errors if "rota" in w]
        self.assertGreaterEqual(len(routes), 2)
        self.assertTrue(any("Order Service" in r or "Auth Service" in r for r in routes))

    def test_shop_baseline_has_no_route_findings(self):
        errors, warnings = lint_layout(ROOT / "tests" / "fixtures" / "shop-baseline.drawio")
        self.assertEqual([m for m in errors + warnings if "rota" in m or "atravessa" in m], [])


class StructureRobustnessTest(unittest.TestCase):
    def test_missing_file_is_not_reported_as_malformed_xml(self):
        errs = validate("/nao/existe/arquivo.drawio")
        self.assertEqual(len(errs), 1)
        self.assertIn("arquivo não encontrado", errs[0])

    def test_diagram_without_graph_model_is_an_error(self):
        errs = validate(write('<mxfile><diagram name="p">dGV4dG8gY29tcHJpbWlkbw==</diagram></mxfile>'))
        self.assertTrue(any("mxGraphModel" in e for e in errs))

    def test_cell_with_dangling_parent_is_an_error(self):
        xml = GOOD.replace('<mxCell id="a" value="A" vertex="1" parent="1">', '<mxCell id="a" value="A" vertex="1" parent="zzz">')
        errs = validate(write(xml))
        self.assertTrue(any("parent inválido: zzz" in e for e in errs))

    def test_object_wrapped_nodes_are_valid_edge_targets(self):
        xml = ('<mxfile><diagram name="p"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
               '<object id="n1" label="Com link" link="https://x"><mxCell vertex="1" parent="1">'
               '<mxGeometry x="0" y="0" width="80" height="40" as="geometry"/></mxCell></object>'
               '<UserObject id="n2" label="Outro"><mxCell vertex="1" parent="1">'
               '<mxGeometry x="200" y="0" width="80" height="40" as="geometry"/></mxCell></UserObject>'
               '<mxCell id="e1" edge="1" source="n1" target="n2" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>'
               '</root></mxGraphModel></diagram></mxfile>')
        self.assertEqual(validate(write(xml)), [])


if __name__ == "__main__":
    unittest.main()
