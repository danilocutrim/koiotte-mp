---
max_turns: 10
timeout_seconds: 120
allowed_tools: [Read, Glob, Grep, Write, Agent]
runs: 3
---
Explique em 3 frases o que esta função faz:

```python
def dedupe(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
```
