#!/usr/bin/env python3
"""Soma tokens por caso e braço a partir do JSON do `claude plugin eval` e dos traces mantidos.

Os traces só existem se o eval rodou com --keep-temp. Sem trace, a linha mostra "trace ausente"
(nunca zero inventado). O custo do juiz LLM (judgeCostUsd) não está no trace e não entra aqui.

Limite medido: output_tokens do trace é o snapshot do início do streaming (stop_reason None), então a
saída é subestimada. Entrada e cache são confiáveis. O número confiável de consumo total é o costUsd.
"""
import collections
import json
import sys
from pathlib import Path

FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def usage_from_trace(path):
    """Tokens por modelo. Mensagem com o mesmo id conta uma vez, com o maior valor de cada campo."""
    per_message = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            msg = event.get("message") if isinstance(event, dict) else None
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            usage, mid = msg.get("usage"), msg.get("id")
            if not usage or not mid:
                continue
            _model, seen = per_message.setdefault(mid, (msg.get("model", "?"), {}))
            for k in FIELDS:
                seen[k] = max(seen.get(k, 0), usage.get(k) or 0)
    totals = collections.defaultdict(collections.Counter)
    for model, seen in per_message.values():
        totals[model].update(seen)
    return totals


def report(result_json):
    data = json.loads(Path(result_json).read_text(encoding="utf-8"))
    rows = []
    for case in data.get("cases", []):
        for arm, runs in case.get("arms", {}).items():
            for i, run in enumerate(runs, 1):
                row = {"case": case["name"], "arm": arm, "run": i, "cost_usd": run.get("costUsd"),
                       "input": None, "cache_write": None, "cache_read": None, "output": None}
                trace = run.get("tracePath")
                if trace and Path(trace).exists():
                    total = collections.Counter()
                    for counter in usage_from_trace(trace).values():
                        total.update(counter)
                    row.update(input=total["input_tokens"], cache_write=total["cache_creation_input_tokens"],
                               cache_read=total["cache_read_input_tokens"], output=total["output_tokens"])
                rows.append(row)
    return rows


def _fmt(v):
    return "trace ausente" if v is None else f"{v:,}".replace(",", ".")


def main(argv):
    if len(argv) != 2:
        print("uso: eval_tokens.py <resultado.json do claude plugin eval>", file=sys.stderr)
        return 2
    try:
        rows = report(argv[1])
    except (OSError, ValueError) as e:
        print(f"erro: não consegui ler {argv[1]}: {e}", file=sys.stderr)
        return 1
    print(f"{'caso':<20}{'braço':<9}{'run':>4}{'entrada':>10}{'cache esc.':>12}{'cache leit.':>13}{'saída (mín.)':>14}{'US$':>8}")
    missing = False
    for r in rows:
        missing = missing or r["input"] is None
        if r["input"] is None:
            tokens = f"{'trace ausente':>44}"
        else:
            tokens = f"{_fmt(r['input']):>10}{_fmt(r['cache_write']):>12}{_fmt(r['cache_read']):>13}{_fmt(r['output']):>14}"
        cost = "-" if r["cost_usd"] is None else f"{r['cost_usd']:.3f}"
        print(f"{r['case']:<20}{r['arm']:<9}{r['run']:>4}{tokens}{cost:>8}")
    print("\nSaída é um piso: o trace guarda o snapshot do início do streaming (medido: um Write de ~590 "
          "tokens aparece como 16). Entrada e cache são confiáveis. Para consumo total, use a coluna US$ "
          "(costUsd do eval, sem o juiz).")
    if missing:
        print("Alguns traces não existem: rode o eval com --keep-temp para guardá-los.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
