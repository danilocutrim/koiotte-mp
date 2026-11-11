#!/usr/bin/env python3
"""Roda o validador/linter de .drawio nos arquivos que cada run do `claude plugin eval` gerou,
mede o que a skill muda (setas rotuladas, grupos, tooltips), com --save guarda cópias estáveis e com
--render checa a rota EXATA das setas (renderiza cada .drawio com o CLI do draw.io e lê o SVG).

Os graders embutidos do eval não executam scripts, então a organização do diagrama é medida aqui,
depois do eval. Exige que o eval tenha rodado com --keep-temp: os arquivos do run ficam em
<dir do trace>/../sealed/home/cwd (o eval os sela com modo 000; este script libera a leitura, como
o próprio eval sugere). Run sem arquivo é reportado como tal, nunca como zero erros.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_drawio import _absolute_rects, _contains, lint_layout, validate  # noqa: E402


def _run_dir(trace_path):
    return Path(trace_path).parent.parent if trace_path else None


def _drawio_files(run_dir):
    sealed = run_dir / "sealed"
    for d in (run_dir, sealed):
        try:
            d.chmod(0o700)
        except OSError:
            pass
    cwd = sealed / "home" / "cwd"
    try:
        return sorted(cwd.rglob("*.drawio")) if cwd.exists() else []
    except OSError:
        return []


def metrics(path):
    """O que a skill muda além de erros de layout: setas rotuladas, grupos e tooltips."""
    zero = {"edges": 0, "labeled_edges": 0, "groups": 0, "tooltips": 0}
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return zero
    out = dict(zero)
    for diagram in root.iter("diagram"):
        cells = {c.get("id"): c for c in diagram.iter("mxCell") if c.get("id")}
        rects = _absolute_rects(cells)
        out["groups"] += sum(1 for i, r in rects.items() if any(_contains(r, o) for j, o in rects.items() if j != i))
        for cell in cells.values():
            if cell.get("edge") == "1":
                out["edges"] += 1
                out["labeled_edges"] += 1 if (cell.get("value") or "").strip() else 0
            elif cell.get("vertex") == "1" and cell.get("tooltip"):
                out["tooltips"] += 1
    return out


def render_and_check(path):
    """Rota exata via SVG do draw.io; None se não há CLI ou a renderização falhou."""
    from route_check import check, render_svg
    svg = render_svg(path)
    return None if svg is None else check(path, svg)


def lint_runs(result_json, save_dir=None, route_checker=None):
    data = json.loads(Path(result_json).read_text(encoding="utf-8"))
    rows = []
    for case in data.get("cases", []):
        for arm, runs in case.get("arms", {}).items():
            for i, run in enumerate(runs, 1):
                row = {"case": case["name"], "arm": arm, "run": i, "files": 0,
                       "errors": None, "warnings": None, "status": "run ausente", "details": [],
                       "edges": 0, "labeled_edges": 0, "groups": 0, "tooltips": 0,
                       "through": None, "crossings": None}
                run_dir = _run_dir(run.get("tracePath"))
                if run_dir is not None and run_dir.exists():
                    files = _drawio_files(run_dir)
                    row["files"] = len(files)
                    if not files:
                        row["status"] = "sem .drawio"
                    else:
                        errors = warnings = 0
                        for n, f in enumerate(files, 1):
                            if save_dir is not None:
                                Path(save_dir).mkdir(parents=True, exist_ok=True)
                                suffix = "" if n == 1 else f"-{n}"
                                shutil.copy(f, Path(save_dir) / f"{case['name']}-{arm}-{i}{suffix}.drawio")
                            for k, v in metrics(f).items():
                                row[k] += v
                            if route_checker is not None:
                                exact = route_checker(f)
                                if exact is not None:
                                    row["through"] = (row["through"] or 0) + len(exact["through"])
                                    row["crossings"] = (row["crossings"] or 0) + len(exact["crossings"])
                                    row["details"] += [f"{f.name}: {m}" for m in exact.get("findings", [])]
                            structural = validate(f)
                            layout_errors, layout_warnings = ([], []) if structural else lint_layout(f)
                            found = structural + layout_errors
                            errors += len(found)
                            warnings += len(layout_warnings)
                            row["details"] += [f"{f.name}: {m}" for m in found + layout_warnings]
                        row.update(errors=errors, warnings=warnings, status="ok")
                rows.append(row)
    return rows


def summarize(rows):
    out = {}
    for r in rows:
        s = out.setdefault(r["arm"], {"runs": 0, "with_file": 0, "clean": 0, "errors": 0, "warnings": 0,
                                      "edges": 0, "labeled_edges": 0, "groups": 0, "tooltips": 0,
                                      "rendered": 0, "no_through": 0, "through": 0, "crossings": 0})
        s["runs"] += 1
        if r.get("through") is not None:
            s["rendered"] += 1
            s["through"] += r["through"]
            s["crossings"] += r["crossings"]
            s["no_through"] += 1 if r["through"] == 0 else 0
        for k in ("edges", "labeled_edges", "groups", "tooltips"):
            s[k] += r[k]
        if r["errors"] is not None:
            s["with_file"] += 1
            s["errors"] += r["errors"]
            s["warnings"] += r["warnings"]
            if r["errors"] == 0:
                s["clean"] += 1
    return out


def main(argv):
    save_dir = None
    render = False
    args = argv[1:]
    if "--render" in args:
        render = True
        args.remove("--render")
    if "--save" in args:
        i = args.index("--save")
        if i + 1 >= len(args):
            print("uso: eval_lint.py <resultado.json> [--save PASTA] [--render]", file=sys.stderr)
            return 2
        save_dir = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print("uso: eval_lint.py <resultado.json do claude plugin eval --keep-temp> [--save PASTA] [--render]",
              file=sys.stderr)
        return 2
    try:
        rows = lint_runs(args[0], save_dir=save_dir, route_checker=render_and_check if render else None)
    except (OSError, ValueError) as e:
        print(f"erro: não consegui ler {args[0]}: {e}", file=sys.stderr)
        return 1
    extra = f"{'por dentro':>11}{'cruz.':>7}" if render else ""
    print(f"{'caso':<22}{'braço':<9}{'run':>4}{'arqs':>6}{'erros':>7}{'avisos':>8}{'rótulos':>9}{'grupos':>8}{'tooltips':>10}{extra}  situação")
    for r in rows:
        e = "-" if r["errors"] is None else r["errors"]
        w = "-" if r["warnings"] is None else r["warnings"]
        lab = f"{r['labeled_edges']}/{r['edges']}"
        more = ""
        if render:
            th = "não renderizado" if r["through"] is None else r["through"]
            cr = "-" if r["crossings"] is None else r["crossings"]
            more = f"{th!s:>11}{cr!s:>7}"
        print(f"{r['case']:<22}{r['arm']:<9}{r['run']:>4}{r['files']:>6}{e!s:>7}{w!s:>8}{lab:>9}{r['groups']:>8}{r['tooltips']:>10}{more}  {r['status']}")
    print()
    for arm, s in summarize(rows).items():
        line = (f"{arm:<9} {s['clean']}/{s['runs']} runs sem erro de layout ({s['with_file']} com .drawio) · "
                f"{s['errors']} erros · {s['warnings']} avisos · setas rotuladas {s['labeled_edges']}/{s['edges']} · "
                f"{s['groups']} grupos · {s['tooltips']} tooltips")
        if render:
            line += (f" · rota exata: {s['no_through']}/{s['rendered']} runs sem seta por dentro de nó, "
                     f"{s['crossings']} cruzamentos")
        print(line)
    if save_dir:
        print(f"\nArquivos copiados para {save_dir} (abra no draw.io para julgar a estética).")
    print("\nSó há dados para runs guardados: rode o eval com --keep-temp. "
          "O linter não julga estética: abra alguns arquivos no draw.io.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
