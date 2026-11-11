#!/usr/bin/env python3
"""Checagem EXATA das rotas das setas de um .drawio, a partir do SVG que o próprio draw.io renderiza.

O linter de validate_drawio.py só prevê a rota (heurística). Aqui a rota é a real: o SVG exportado pelo
CLI do draw.io traz, para cada célula, um <g data-cell-id> com o caminho da seta (M/L/Q). Com isso:
  - erro: uma seta passa por dentro de um nó que não é a origem nem o destino (nem um grupo);
  - aviso: cruzamentos entre setas (contagem e pares).

Exige o CLI `drawio`. Sem ele, diz que o diagrama não foi renderizado (exit 3). O CLI abre o draw.io por
alguns segundos; erros de GPU no log são ruído.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_drawio import _absolute_rects, _contains, _short, _label, _segment_hits_rect  # noqa: E402

SVG = "{http://www.w3.org/2000/svg}"
_NUM = r"-?\d+(?:\.\d+)?"


def drawio_path():
    return shutil.which("drawio") or shutil.which("draw.io")


def render_svg(drawio_file, timeout=90):
    """Renderiza o .drawio para SVG com o CLI e devolve o texto do SVG (None se não houver CLI/falhar)."""
    exe = drawio_path()
    if not exe:
        return None
    out = Path(tempfile.mkdtemp()) / "route-check.svg"
    try:
        subprocess.run([exe, "-x", "-f", "svg", "-o", str(out), str(drawio_file)],
                       capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return out.read_text(encoding="utf-8") if out.exists() else None


def parse_path(d):
    """Vértices da rota. Em curvas Q (cantos arredondados) o ponto de controle é o canto da rota ortogonal."""
    tokens = re.findall(r"[MLQC]|" + _NUM, d)
    points, i, cmd = [], 0, None
    while i < len(tokens):
        if tokens[i] in "MLQC":
            cmd = tokens[i]
            i += 1
            continue
        take = {"M": 2, "L": 2, "Q": 4, "C": 6}.get(cmd)
        nums = tokens[i:i + take] if take else []
        if not take or len(nums) < take or any(n in "MLQC" for n in nums):
            break
        v = [float(n) for n in nums]
        if cmd == "Q":
            points += [(v[0], v[1]), (v[2], v[3])]
        else:
            points.append((v[-2], v[-1]))
        i += take
    return points


def _svg_geometry(svg_text):
    root = ET.fromstring(svg_text)
    rects, routes = {}, {}
    for g in root.iter(SVG + "g"):
        cid = g.get("data-cell-id")
        if not cid:
            continue
        rect = g.find(f".//{SVG}rect[@width]")
        if rect is not None and rect.get("fill") != "none":
            rects[cid] = (float(rect.get("x", 0)), float(rect.get("y", 0)),
                          float(rect.get("width")), float(rect.get("height")))
        for path in g.iter(SVG + "path"):
            if path.get("fill") == "none" and path.get("d") and path.get("stroke") not in (None, "none"):
                pts = parse_path(path.get("d"))
                if len(pts) >= 2:
                    routes[cid] = pts
                    break
    return rects, routes


def _crosses(p1, p2, p3, p4):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return o(p1, p2, p3) * o(p1, p2, p4) < 0 and o(p3, p4, p1) * o(p3, p4, p2) < 0


def _svg_offset(svg_rects, geo_rects):
    """Deslocamento entre a página do .drawio e o SVG exportado (que é recortado no conteúdo).

    Vem dos nós presentes nos dois lados; serve para os nós sem <rect> no SVG (texto, cilindro),
    cuja posição só se conhece pela geometria do .drawio. Usa o deslocamento mais comum."""
    counts = {}
    for cid, (x, y, w, h) in svg_rects.items():
        geo = geo_rects.get(cid)
        if geo and abs(geo[2] - w) <= 1 and abs(geo[3] - h) <= 1:
            key = (round(x - geo[0]), round(y - geo[1]))
            counts[key] = counts.get(key, 0) + 1
    return max(counts, key=counts.get) if counts else (0, 0)


def check(drawio_file, svg_text):
    """{'through': [msg], 'crossings': [(edge_a, edge_b)], 'findings': [msg]}"""
    try:
        diagram = ET.parse(drawio_file).getroot()
    except (ET.ParseError, OSError):
        return {"through": [], "crossings": [], "findings": []}
    svg_rects, routes = _svg_geometry(svg_text)
    through, edges_in_order = [], []
    for page in diagram.iter("diagram"):
        cells = {c.get("id"): c for c in page.iter("mxCell") if c.get("id")}
        geo_rects = _absolute_rects(cells)
        groups = {i for i, r in geo_rects.items() if any(_contains(r, o) for j, o in geo_rects.items() if j != i)}
        dx, dy = _svg_offset(svg_rects, geo_rects)
        obstacles = {i: svg_rects.get(i, (r[0] + dx, r[1] + dy, r[2], r[3]))
                     for i, r in geo_rects.items() if i not in groups}
        names = {i: _short(_label(c), 30) for i, c in cells.items()}
        for eid, cell in cells.items():
            if cell.get("edge") != "1" or eid not in routes:
                continue
            src, tgt = cell.get("source"), cell.get("target")
            edges_in_order.append(eid)
            segments = list(zip(routes[eid], routes[eid][1:]))
            for nid, rect in obstacles.items():
                if nid in (src, tgt):
                    continue
                if any(_segment_hits_rect(a, b, rect) for a, b in segments):
                    through.append(f"a seta {eid} ({names.get(src, src)} -> {names.get(tgt, tgt)}) "
                                   f"passa por dentro do nó {names[nid]}")
    crossings = []
    for i, a in enumerate(edges_in_order):
        for b in edges_in_order[i + 1:]:
            sa, sb = list(zip(routes[a], routes[a][1:])), list(zip(routes[b], routes[b][1:]))
            if any(_crosses(p1, p2, p3, p4) for p1, p2 in sa for p3, p4 in sb):
                crossings.append((a, b))
    findings = list(through)
    if crossings:
        findings.append(f"{len(crossings)} cruzamento(s) entre setas: " + ", ".join(f"{a}×{b}" for a, b in crossings[:6]))
    return {"through": through, "crossings": crossings, "findings": findings}


def main(argv):
    if len(argv) != 2:
        print("uso: route_check.py <arquivo.drawio>", file=sys.stderr)
        return 2
    svg = render_svg(argv[1])
    if svg is None:
        print("o diagrama não foi renderizado (CLI `drawio` ausente ou falhou): rota real não verificada")
        return 3
    result = check(argv[1], svg)
    for f in result["findings"]:
        print(("erro: " if "passa por dentro" in f else "aviso: ") + f)
    if result["through"]:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
