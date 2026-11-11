#!/usr/bin/env python3
"""Valida um arquivo .drawio.

validate(): estrutura (XML bem formado, IDs únicos por página, arestas com nós existentes).
lint_layout(): organização visual que dá para checar sem renderizar:
  - erro: seta reta (sem edgeStyle) que atravessa um nó que não é a origem nem o destino;
  - aviso: rota ortogonal provável (ou as duas rotas em L) cortando um nó; texto que provavelmente
    não cabe na caixa;
    várias setas com o mesmo rótulo saindo do mesmo nó; nó dentro da área de um grupo sem ser filho
    dele; seta entre contêineres diferentes fora de parent="1"; coordenadas fora da grade de 10.

Limites do linter: não julga estética e NÃO sabe qual rota o draw.io escolherá (a previsão foi calibrada
em poucos diagramas e já errou em dois casos reais), por isso achados de rota ortogonal são só avisos:
a renderização é quem confirma. Setas com waypoints não são checadas (exceto se origem e destino estão
alinhados).
"""
import html
import math
import re
import sys
import xml.etree.ElementTree as ET

CHAR_W = 7      # largura média de um caractere (fonte 12 px)
LINE_H = 16     # altura de uma linha de texto
PAD = 10        # margem interna da caixa
ALIGN_TOL = 2   # tolerância (px) para considerar origem e destino alinhados
SHRINK = 2      # tocar a borda de um nó não conta como atravessar


def _cells(diagram):
    """(id, mxCell) de cada célula; nós envolvidos em <object>/<UserObject> usam o id do invólucro."""
    wrapped = set()
    out = []
    for el in diagram.iter():
        if el.tag in ("object", "UserObject"):
            inner = el.find("mxCell")
            if inner is not None:
                wrapped.add(id(inner))
                out.append((el.get("id"), inner))
    for el in diagram.iter("mxCell"):
        if id(el) not in wrapped:
            out.append((el.get("id"), el))
    return out


def validate(path):
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        return [f"arquivo não encontrado: {path}"]
    except (ET.ParseError, OSError) as e:
        return [f"XML mal formado: {e}"]
    if root.tag != "mxfile":
        return ["raiz deve ser <mxfile>"]
    errors = []
    diagrams = list(root.iter("diagram"))
    if not diagrams:
        errors.append("nenhum <diagram> encontrado")
    for diagram in diagrams:
        name = diagram.get("name", "?")
        if diagram.find("mxGraphModel") is None:
            errors.append(f"[{name}] <diagram> sem mxGraphModel (conteúdo comprimido ou inválido)")
            continue
        cells = _cells(diagram)
        ids = set()
        for cid, _cell in cells:
            if cid is None:
                errors.append(f"[{name}] mxCell sem id")
            elif cid in ids:
                errors.append(f"[{name}] id duplicado: {cid}")
            ids.add(cid)
        for cid, cell in cells:
            parent = cell.get("parent")
            if parent is not None and parent not in ids:
                errors.append(f"[{name}] célula {cid} com parent inválido: {parent}")
            if cell.get("edge") == "1":
                for attr in ("source", "target"):
                    ref = cell.get(attr)
                    if ref is None or ref not in ids:
                        errors.append(f"[{name}] aresta {cid} com {attr} inválido: {ref}")
    return errors


def _geometry(cell):
    g = cell.find("mxGeometry")
    if g is None or g.get("x") is None and g.get("y") is None and g.get("width") is None:
        return None
    return (float(g.get("x", 0)), float(g.get("y", 0)), float(g.get("width", 0)), float(g.get("height", 0)))


def _absolute_rects(cells):
    """id -> (x, y, w, h) absolutos, somando os offsets dos pais."""
    own = {}
    parent = {}
    for cid, cell in cells.items():
        if cell.get("vertex") == "1":
            geo = _geometry(cell)
            if geo and geo[2] > 0 and geo[3] > 0:
                own[cid] = geo
                parent[cid] = cell.get("parent")

    def absolute(cid, depth=0):
        x, y, w, h = own[cid]
        p = parent.get(cid)
        if p in own and depth < 20:
            px, py, _, _ = absolute(p, depth + 1)
            x, y = x + px, y + py
        return (x, y, w, h)

    return {cid: absolute(cid) for cid in own}


def _contains(outer, inner):
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[0] + outer[2] >= inner[0] + inner[2] and outer[1] + outer[3] >= inner[1] + inner[3]
            and outer != inner)


def _segment_hits_rect(p, q, rect):
    x, y, w, h = rect
    x, y, w, h = x + SHRINK, y + SHRINK, w - 2 * SHRINK, h - 2 * SHRINK
    if w <= 0 or h <= 0:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x), (dx, x + w - p[0]), (-dy, p[1] - y), (dy, y + h - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return t0 < t1


def _l_routes(p, q):
    """As duas rotas em L entre dois centros: horizontal-vertical e vertical-horizontal."""
    return [[(p, (q[0], p[1])), ((q[0], p[1]), q)],
            [(p, (p[0], q[1])), ((p[0], q[1]), q)]]


def _overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0) > 0


def _predicted_route(src_rect, tgt_rect, p, q):
    """Rota que o draw.io costuma tomar com orthogonalEdgeStyle (calibrada em diagramas reais):
    sobreposição horizontal => sai pela vertical (V-H-V); sobreposição vertical => sai pela horizontal
    (H-V-H); disjuntas nos dois eixos => horizontal primeiro (H-V). None se as caixas se sobrepõem."""
    sx, sy, sw, sh = src_rect
    tx, ty, tw, th = tgt_rect
    over_x = _overlap(sx, sx + sw, tx, tx + tw)
    over_y = _overlap(sy, sy + sh, ty, ty + th)
    if over_x and over_y:
        return None
    if over_x:
        mid = ((sy + sh) + ty) / 2 if q[1] > p[1] else ((ty + th) + sy) / 2
        a, b = (p[0], mid), (q[0], mid)
        return [(p, a), (a, b), (b, q)]
    if over_y:
        mid = ((sx + sw) + tx) / 2 if q[0] > p[0] else ((tx + tw) + sx) / 2
        a, b = (mid, p[1]), (mid, q[1])
        return [(p, a), (a, b), (b, q)]
    corner = (q[0], p[1])
    return [(p, corner), (corner, q)]


def _blockers(route, rects, skip):
    return [nid for nid, rect in rects.items()
            if nid not in skip and any(_segment_hits_rect(a, b, rect) for a, b in route)]


def _port(rect, style, kind):
    """Ponto onde a seta sai (kind='exit') ou chega ('entry'): a porta explícita do estilo
    (exitX/exitY, entryX/entryY, frações da caixa) ou, sem ela, o centro."""
    x, y, w, h = rect
    fx = re.search(rf"(?:^|;){kind}X=(-?[\d.]+)", style)
    fy = re.search(rf"(?:^|;){kind}Y=(-?[\d.]+)", style)
    if fx and fy:
        return (x + float(fx.group(1)) * w, y + float(fy.group(1)) * h)
    return (x + w / 2, y + h / 2)


def _ancestors(cid, parents):
    out, seen = [], set()
    while parents.get(cid) and parents[cid] not in seen:
        cid = parents[cid]
        seen.add(cid)
        out.append(cid)
    return out


def _label(cell):
    raw = cell.get("value") or ""
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).replace("\xa0", " ")


def _short(text, n=40):
    one = " ".join(text.split())
    return one if len(one) <= n else one[: n - 1] + "…"


def lint_layout(path):
    """Devolve (erros, avisos). Arquivo ilegível não gera achados: validate() já o reporta."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return [], []
    errors, warnings = [], []
    for diagram in root.iter("diagram"):
        name = diagram.get("name", "?")
        cells = {c.get("id"): c for c in diagram.iter("mxCell") if c.get("id")}
        rects = _absolute_rects(cells)
        groups = {i for i, r in rects.items() if any(_contains(r, o) for j, o in rects.items() if j != i)}

        parents = {cid: c.get("parent") for cid, c in cells.items()}
        names = {cid: _short(_label(c), 30) for cid, c in cells.items()}

        for eid, cell in cells.items():
            if cell.get("edge") != "1":
                continue
            src, tgt = cell.get("source"), cell.get("target")
            if src not in rects or tgt not in rects:
                continue
            style = cell.get("style") or ""
            has_points = cell.find("mxGeometry/Array") is not None
            p = _port(rects[src], style, "exit")
            q = _port(rects[tgt], style, "entry")
            routed = has_points or "edgeStyle" in style
            aligned = abs(p[0] - q[0]) <= ALIGN_TOL or abs(p[1] - q[1]) <= ALIGN_TOL
            # a seta sai e chega na borda: o que está dentro da origem ou do destino não está no caminho
            inside = {cid for cid in rects if {src, tgt} & set(_ancestors(cid, parents))}
            skip = groups | {src, tgt} | inside
            head = f"[{name}] aresta {eid} ({_short(_label(cells[src]), 25)} -> {_short(_label(cells[tgt]), 25)})"
            if has_points:
                continue
            if routed and not aligned:
                blocked = [_blockers(r, rects, skip) for r in _l_routes(p, q)]
                if all(blocked):
                    warnings.append(f"{head}: nenhuma rota ortogonal simples (em L) evita o nó {names[blocked[0][0]]}; "
                                    f"o draw.io pode contornar, confira na renderização")
                    continue
                predicted = _predicted_route(rects[src], rects[tgt], p, q)
                hit = _blockers(predicted, rects, skip) if predicted else []
                if hit:
                    warnings.append(f"{head}: a rota ortogonal provável atravessa o nó {names[hit[0]]}")
                continue
            for nid in _blockers([(p, q)], rects, skip):
                errors.append(f"{head} atravessa o nó {names[nid]}")

        # contêiner de verdade: filhos com parent, e setas entre contêineres no nível raiz
        for gid in sorted(groups):
            for nid, rect in rects.items():
                if nid != gid and nid not in groups and _contains(rects[gid], rect) and gid not in _ancestors(nid, parents):
                    warnings.append(f"[{name}] o nó {names[nid]} está na área do grupo {names[gid]} mas não é filho dele "
                                    f"(use parent=\"{gid}\" com coordenadas relativas)")
        for eid, cell in cells.items():
            if cell.get("edge") == "1" and cell.get("source") in rects and cell.get("target") in rects:
                if parents.get(cell.get("source")) != parents.get(cell.get("target")) and cell.get("parent") != "1":
                    warnings.append(f"[{name}] a aresta {eid} liga contêineres diferentes e deve ter parent=\"1\"")

        # rótulos repetidos saindo do mesmo nó
        by_source = {}
        for cell in cells.values():
            label = (cell.get("value") or "").strip()
            if cell.get("edge") == "1" and label and cell.get("source") in cells:
                by_source.setdefault((cell.get("source"), label), 0)
                by_source[(cell.get("source"), label)] += 1
        for (source, label), count in by_source.items():
            if count >= 2:
                warnings.append(f"[{name}] o nó {names[source]} tem {count} setas com o mesmo rótulo \"{label}\"; "
                                f"dê um rótulo próprio a cada uma")

        # grade de 10
        off = []
        for cid, cell in cells.items():
            geo = _geometry(cell) if cell.get("vertex") == "1" else None
            if geo and any(abs(v / 10 - round(v / 10)) > 1e-6 for v in geo):
                off.append(names[cid])
        if off:
            warnings.append(f"[{name}] {len(off)} nós com posição ou tamanho fora da grade de 10 (ex.: {off[0]})")

        for nid, rect in rects.items():
            cell = cells[nid]
            text = _label(cell)
            if not text.strip() or (cell.get("style") or "").startswith("text;"):
                continue
            avail = max(rect[2] - PAD, 1)
            wrap = "whiteSpace=wrap" in (cell.get("style") or "")
            lines = 0
            too_wide = False
            for line in text.splitlines() or [""]:
                need = len(line) * CHAR_W
                if wrap:
                    lines += max(1, math.ceil(need / avail))
                else:
                    lines += 1
                    too_wide = too_wide or need > avail
            too_tall = lines * LINE_H + PAD > rect[3]
            if too_wide or too_tall:
                warnings.append(f"[{name}] o texto do nó \"{_short(text)}\" provavelmente não cabe "
                                f"(≈{lines} linhas em {int(rect[2])}x{int(rect[3])}px)")
    return errors, warnings


def main(argv):
    if len(argv) != 2:
        print("uso: validate_drawio.py <arquivo.drawio>", file=sys.stderr)
        return 2
    errors = validate(argv[1])
    layout_errors, warnings = ([], []) if errors else lint_layout(argv[1])
    errors = errors + layout_errors
    for w in warnings:
        print(f"aviso: {w}")
    if errors:
        print("\n".join(errors))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
