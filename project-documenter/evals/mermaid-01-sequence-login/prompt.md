---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Skill]
runs: 3
---
Crie `docs/diagrams/auth/flow.md` com exatamente este conteúdo:

```markdown
# auth — Fluxo

## Visão geral
Login de usuários.

## Componentes
- **Cliente** (web) — navegador do usuário.
- **API** (Go) — serviço de autenticação.
- **Banco de dados** (Postgres) — usuários.

## Fluxos principais
### Login
1. O Cliente chama `POST /login` na API.
2. A API consulta o usuário no Banco de dados.
3. O Banco de dados devolve o usuário.
4. A API devolve um token ao Cliente.

## Integrações externas
Nada encontrado.

## Infra e deploy
Nada encontrado.

## Lacunas e dúvidas
- Nenhuma.
```

Depois gere o diagrama de sequência do fluxo "Login" em Mermaid em `docs/diagrams/auth/sequence-login.mmd`.
