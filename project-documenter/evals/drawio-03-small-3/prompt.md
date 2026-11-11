---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Skill, "Bash(python3 \"/home/danilo/Workspace/project-documenter/scripts/validate_drawio.py\":*)"]
runs: 3
---
Crie `docs/diagrams/notes/flow.md` com exatamente este conteúdo:

```markdown
# notes — Fluxo

## Visão geral
App de notas simples.

## Componentes
- **Frontend** (React) — interface de notas.
- **API** (Node) — CRUD de notas.
- **Postgres** — armazena as notas.

## Fluxos principais
### Salvar nota
1. O Frontend chama a API.
2. A API grava no Postgres.

## Integrações externas
Nada encontrado.

## Infra e deploy
Nada encontrado.

## Lacunas e dúvidas
- Nenhuma.
```

Depois gere o diagrama de arquitetura em draw.io em `docs/diagrams/notes/architecture-notes.drawio`, a partir da seção Componentes.
