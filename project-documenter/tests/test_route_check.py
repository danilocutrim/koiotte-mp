import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import route_check as rc  # noqa: E402


def drawio_xml(nodes, edges):
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for nid, label, x, y, w, h, *rest in nodes:
        parent = rest[0] if rest else "1"
        cells.append(f'<mxCell id="{nid}" value="{label}" style="rounded=1;" vertex="1" parent="{parent}">'
                     f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    for eid, src, tgt in edges:
        cells.append(f'<mxCell id="{eid}" style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" '
                     f'source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    return ('<mxfile><diagram name="t"><mxGraphModel><root>' + "".join(cells) + '</root></mxGraphModel></diagram></mxfile>')


def svg_xml(nodes, routes):
    """nodes: (id, x, y, w, h); routes: id -> path d (a seta tem um path de rota e um de ponta)."""
    parts = ['<svg xmlns="http://www.w3.org/2000/svg"><g>']
    for nid, x, y, w, h in nodes:
        parts.append(f'<g data-cell-id="{nid}"><g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" ry="9"/></g></g>')
    for eid, d in routes.items():
        parts.append(f'<g data-cell-id="{eid}"><g transform="translate(0.5,0.5)"><path d="{d}" fill="none" stroke="#000"/>'
                     f'<path d="M 0 0 L 4 8 L 8 0 Z" fill="#000" stroke="#000"/></g></g>')
    parts.append("</g></svg>")
    return "".join(parts)


def write(text, suffix):
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


ROW_NODES = [("A", "Alfa", 0, 0, 100, 60), ("B", "Beta", 200, 0, 100, 60), ("C", "Gama", 400, 0, 100, 60)]
ROW_SVG = [("A", 0, 0, 100, 60), ("B", 200, 0, 100, 60), ("C", 400, 0, 100, 60)]


class ParsePathTest(unittest.TestCase):
    def test_lines(self):
        self.assertEqual(rc.parse_path("M 0 0 L 0 90 L 50 90"), [(0, 0), (0, 90), (50, 90)])

    def test_rounded_corner_uses_the_control_point_as_the_corner(self):
        self.assertEqual(rc.parse_path("M 0 0 L 0 90 Q 0 100 10 100 L 20 100"),
                         [(0, 0), (0, 90), (0, 100), (10, 100), (20, 100)])

    def test_curve_keeps_only_the_endpoint(self):
        self.assertEqual(rc.parse_path("M 0 0 C 1 1 2 2 30 40"), [(0, 0), (30, 40)])

    def test_garbage_is_empty(self):
        self.assertEqual(rc.parse_path("isto não é path"), [])


class CheckTest(unittest.TestCase):
    def check(self, nodes, svg_nodes, edges, routes):
        return rc.check(write(drawio_xml(nodes, edges), ".drawio"), svg_xml(svg_nodes, routes))

    def test_route_through_a_third_node_is_reported(self):
        r = self.check(ROW_NODES, ROW_SVG, [("e", "A", "C")], {"e": "M 100 30 L 400 30"})
        self.assertEqual(len(r["through"]), 1)
        self.assertIn("Beta", r["through"][0])

    def test_route_that_detours_is_clean(self):
        route = "M 50 60 L 50 100 Q 50 110 60 110 L 440 110 Q 450 110 450 100 L 450 60"
        r = self.check(ROW_NODES, ROW_SVG, [("e", "A", "C")], {"e": route})
        self.assertEqual(r["through"], [])

    def test_rounded_corner_inside_a_node_is_caught_by_the_control_point(self):
        # os pontos finais estão livres, mas o canto (ponto de controle) cai dentro de B
        route = "M 50 60 L 50 70 Q 250 30 250 80 L 450 80"
        nodes = [("A", "Alfa", 0, 0, 100, 60), ("B", "Beta", 200, 0, 100, 60), ("C", "Gama", 400, 0, 100, 60)]
        r = self.check(nodes, ROW_SVG, [("e", "A", "C")], {"e": route})
        self.assertEqual(len(r["through"]), 1)

    def test_group_container_is_not_an_obstacle(self):
        nodes = [("G", "Grupo", -20, -20, 560, 100), ("A", "Alfa", 0, 0, 100, 60, "G"), ("B", "Beta", 200, 0, 100, 60, "G")]
        svg_nodes = [("G", -20, -20, 560, 100), ("A", 0, 0, 100, 60), ("B", 200, 0, 100, 60)]
        r = self.check(nodes, svg_nodes, [("e", "A", "B")], {"e": "M 100 30 L 200 30"})
        self.assertEqual(r["through"], [])

    def test_crossing_edges_are_counted(self):
        nodes = [("A", "A", 0, 40, 20, 20), ("B", "B", 200, 40, 20, 20), ("C", "C", 90, 0, 20, 20), ("D", "D", 90, 100, 20, 20)]
        svg_nodes = [("A", 0, 40, 20, 20), ("B", 200, 40, 20, 20), ("C", 90, 0, 20, 20), ("D", 90, 100, 20, 20)]
        r = self.check(nodes, svg_nodes, [("e1", "A", "B"), ("e2", "C", "D")],
                       {"e1": "M 20 50 L 200 50", "e2": "M 100 20 L 100 100"})
        self.assertEqual(r["crossings"], [("e1", "e2")])

    def test_edges_that_only_touch_at_a_shared_node_do_not_cross(self):
        nodes = [("H", "H", 100, 40, 20, 20), ("A", "A", 0, 0, 20, 20), ("B", "B", 200, 0, 20, 20)]
        svg_nodes = [("H", 100, 40, 20, 20), ("A", 0, 0, 20, 20), ("B", 200, 0, 20, 20)]
        r = self.check(nodes, svg_nodes, [("e1", "H", "A"), ("e2", "H", "B")],
                       {"e1": "M 110 40 L 110 10 L 20 10", "e2": "M 110 40 L 110 10 L 200 10"})
        self.assertEqual(r["crossings"], [])

    def test_edge_missing_from_the_svg_is_ignored(self):
        r = self.check(ROW_NODES, ROW_SVG, [("e", "A", "C")], {})
        self.assertEqual((r["through"], r["crossings"]), ([], []))

    def test_findings_text(self):
        r = self.check(ROW_NODES, ROW_SVG, [("e", "A", "C")], {"e": "M 100 30 L 400 30"})
        self.assertTrue(any("passa por dentro" in f for f in r["findings"]))

    # O SVG exportado é recortado (deslocado) em relação à página; nó sem <rect> no SVG (texto,
    # cilindro) usa a geometria do .drawio, que precisa ser trazida para as coordenadas do SVG.
    SHIFTED = [("A", "Alfa", 20, 20, 100, 60), ("C", "Gama", 420, 20, 100, 60)]
    SHIFTED_SVG = [("A", 0, 0, 100, 60), ("C", 400, 0, 100, 60)]

    def test_node_without_svg_rect_is_shifted_into_svg_coordinates(self):
        # T fica acima da seta no SVG (y 0..20); sem o deslocamento, a geometria do .drawio (y 20..40) a cruzaria
        nodes = self.SHIFTED + [("T", "texto", 220, 20, 60, 20)]
        r = self.check(nodes, self.SHIFTED_SVG, [("e", "A", "C")], {"e": "M 100 30 L 400 30"})
        self.assertEqual(r["through"], [])

    def test_shifted_node_without_svg_rect_on_the_route_is_reported(self):
        nodes = self.SHIFTED + [("T", "texto", 220, 40, 60, 20)]
        r = self.check(nodes, self.SHIFTED_SVG, [("e", "A", "C")], {"e": "M 100 30 L 400 30"})
        self.assertEqual(len(r["through"]), 1)
        self.assertIn("texto", r["through"][0])


class CliTest(unittest.TestCase):
    def test_without_the_drawio_cli_it_says_it_was_not_rendered(self):
        path = write(drawio_xml(ROW_NODES, []), ".drawio")
        env = dict(os.environ, PATH="/nonexistent")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "route_check.py"), path],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 3)
        self.assertIn("não foi renderizado", r.stdout)

    def test_bad_args(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "route_check.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


@unittest.skipUnless(os.environ.get("RENDER_TESTS") == "1" and rc.drawio_path(),
                     "defina RENDER_TESTS=1 e instale o CLI do draw.io (abre janelas por alguns segundos)")
class RealRenderTest(unittest.TestCase):
    def run_check(self, name):
        fixture = ROOT / "tests" / "fixtures" / name
        return rc.check(fixture, rc.render_svg(fixture))

    def test_old_skill_diagram_has_arrows_through_nodes(self):
        r = self.run_check("shop-with-skill.drawio")
        self.assertGreaterEqual(len(r["through"]), 2)
        self.assertTrue(any("Order Service" in t for t in r["through"]))

    def test_baseline_has_no_arrow_through_a_node(self):
        self.assertEqual(self.run_check("shop-baseline.drawio")["through"], [])

    def test_tiers_diagram_has_no_arrow_through_a_node(self):
        self.assertEqual(self.run_check("shop-tiers-skill.drawio")["through"], [])


if __name__ == "__main__":
    unittest.main()
