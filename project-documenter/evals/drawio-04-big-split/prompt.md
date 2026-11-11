---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Skill, "Bash(python3 \"/home/danilo/Workspace/project-documenter/scripts/validate_drawio.py\":*)"]
runs: 3
---
Crie `docs/diagrams/mega/flow.md` com exatamente este conteúdo:

```markdown
# mega — Fluxo

## Visão geral
Plataforma com três domínios.

## Componentes
Domínio billing:
- **billing-api** (Go) — API de cobrança.
- **invoice-worker** (Go) — gera faturas.
- **ledger-db** (Postgres) — razão contábil.
- **billing-queue** (SQS) — eventos de cobrança.
- **tax-service** (Kotlin) — cálculo de impostos.
- **dunning-job** (Python) — cobranças em atraso.
- **billing-cache** (Redis) — cache de preços.
- **billing-admin** (React) — backoffice de cobrança.

Domínio catalog:
- **catalog-api** (Python) — API de produtos.
- **search-index** (OpenSearch) — busca.
- **catalog-db** (Postgres) — produtos.
- **image-service** (Go) — imagens.
- **image-bucket** (S3) — arquivos de imagem.
- **pricing-service** (Kotlin) — preços.
- **catalog-admin** (React) — backoffice de catálogo.

Domínio shipping:
- **shipping-api** (Kotlin) — API de entregas.
- **carrier-adapter** (Go) — integra transportadoras.
- **shipping-db** (Postgres) — entregas.
- **tracking-worker** (Go) — atualiza rastreio.
- **shipping-queue** (SQS) — eventos de entrega.
- **label-service** (Python) — etiquetas.
- **shipping-admin** (React) — backoffice de entregas.

## Fluxos principais
### Fechar pedido
1. billing-api cobra e publica em billing-queue; invoice-worker gera a fatura.
2. shipping-api cria a entrega; carrier-adapter chama a transportadora.

## Integrações externas
Nada encontrado.

## Infra e deploy
Nada encontrado.

## Lacunas e dúvidas
- Nenhuma.
```

Depois gere o diagrama de arquitetura em draw.io em `docs/diagrams/mega/architecture-mega.drawio`, a partir da seção Componentes.
