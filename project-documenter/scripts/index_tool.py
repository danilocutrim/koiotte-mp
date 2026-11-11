#!/usr/bin/env python3
"""Mantém docs/diagrams/<escopo>/INDEX.md: hashes da seção de origem e do arquivo gerado."""
import hashlib
import sys
from datetime import date
from pathlib import Path

HEADER = ["Diagrama", "Tipo", "Formato", "Origem", "Gerado em", "Hash origem", "Hash arquivo"]


def _scan(text):
    """Seções por título ('H2' e 'H2 › H3'), ignorando '#' dentro de cercas de código. Devolve (seções, duplicados)."""
    secs, dups = {}, set()
    h2 = h3 = None
    in_fence = False

    def open_section(key):
        if key in secs:
            dups.add(key)
        secs.setdefault(key, [])

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        heading = not in_fence and (line.startswith("### ") or line.startswith("## "))
        if heading and line.startswith("### "):
            if h2 is None:
                continue
            h3 = line[4:].strip()
            open_section(f"{h2} › {h3}")
            secs[f"{h2} › {h3}"].append(line)
            secs[h2].append(line)
        elif heading:
            h2 = line[3:].strip()
            h3 = None
            open_section(h2)
            secs[h2].append(line)
        elif h2 is not None:
            secs[h2].append(line)
            if h3 is not None:
                secs[f"{h2} › {h3}"].append(line)
    return {k: "\n".join(v).strip() for k, v in secs.items()}, dups


def parse_sections(text):
    return _scan(text)[0]


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def section_hash(text, key):
    """key pode juntar várias seções com ' + ' (ex.: 'Componentes + Integrações externas')."""
    secs = parse_sections(text)
    body = "\n\n".join(secs[part.strip()] for part in key.split(" + "))
    return _digest(body.encode("utf-8"))


def _file_hash(path):
    return _digest(Path(path).read_bytes())


def _read_rows(index):
    if not index.exists():
        return []
    rows = []
    for line in index.read_text(encoding="utf-8").splitlines()[2:]:
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _valid(rows):
    return [r for r in rows if len(r) == len(HEADER)]


def _write_rows(index, rows):
    out = ["| " + " | ".join(HEADER) + " |", "|" + "---|" * len(HEADER)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    index.write_text("\n".join(out) + "\n", encoding="utf-8")


def add(scope_dir, diagram, type_, fmt, origin, today=None):
    scope_dir = Path(scope_dir)
    for field in (diagram, type_, fmt, origin):
        if "|" in field or "\n" in field or "\r" in field:
            raise ValueError(f"campo não pode conter '|' nem quebra de linha: {field!r}")
    if not (scope_dir / diagram).is_file():
        raise ValueError(f"arquivo do diagrama não existe: {diagram}")
    flow = scope_dir / "flow.md"
    try:
        flow_text = flow.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"não consegui ler flow.md ({e.__class__.__name__}): {flow}")
    _secs, dups = _scan(flow_text)
    for part in origin.split(" + "):
        if part.strip() in dups:
            raise ValueError(f"título duplicado em flow.md: {part.strip()} (renomeie para ficar único)")
    try:
        origin_hash = section_hash(flow_text, origin)
    except KeyError:
        raise ValueError(f"seção de origem não encontrada em flow.md: {origin}")
    index = scope_dir / "INDEX.md"
    existing = _read_rows(index)
    if len(_valid(existing)) != len(existing):
        raise ValueError("INDEX.md tem linha inválida (colunas a menos); corrija antes de adicionar")
    row = [diagram, type_, fmt, origin, today or date.today().isoformat(),
           origin_hash, _file_hash(scope_dir / diagram)]
    rows = [r for r in existing if r[0] != diagram]
    rows.append(row)
    _write_rows(index, rows)


def check(scope_dir):
    scope_dir = Path(scope_dir)
    flow_path = scope_dir / "flow.md"
    try:
        flow = flow_path.read_text(encoding="utf-8")
        dups = _scan(flow)[1]
    except (OSError, UnicodeDecodeError):
        flow, dups = None, set()
    result = []
    for row in _read_rows(scope_dir / "INDEX.md"):
        if len(row) != len(HEADER):
            result.append((row[0] if row and row[0] else "(linha inválida)", ["linha-inválida"]))
            continue
        diagram, _t, _f, origin, _d, h_origin, h_file = row
        flags = []
        target = scope_dir / diagram
        if not target.is_file():
            flags.append("arquivo-ausente")
        elif _file_hash(target) != h_file:
            flags.append("editado-à-mão")
        if flow is None:
            flags.append("flow-ausente")
        else:
            try:
                if any(part.strip() in dups for part in origin.split(" + ")):
                    flags.append("origem-ambígua")
                elif section_hash(flow, origin) != h_origin:
                    flags.append("desatualizado")
            except KeyError:
                flags.append("origem-removida")
        result.append((diagram, flags))
    return result


def main(argv):
    if len(argv) > 1 and argv[1] == "add":
        if len(argv) != 7:
            print("uso: index_tool.py add <dir> <diagrama> <tipo> <formato> <origem>", file=sys.stderr)
            return 2
        try:
            add(Path(argv[2]), argv[3], argv[4], argv[5], argv[6])
        except ValueError as e:
            print(f"erro: {e}", file=sys.stderr)
            return 1
        return 0
    if len(argv) == 3 and argv[1] == "check":
        if not (Path(argv[2]) / "INDEX.md").exists():
            print("sem INDEX.md neste escopo")
            return 0
        for diagram, flags in check(argv[2]):
            print(f"{diagram}\t{'+'.join(flags) if flags else 'ok'}")
        return 0
    print("uso: index_tool.py add <dir> <diagrama> <tipo> <formato> <origem> | check <dir>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
