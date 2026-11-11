---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Skill, "Bash(python3 \"/home/danilo/Workspace/project-documenter/scripts/validate_drawio.py\":*)"]
runs: 3
---
Crie `docs/diagrams/shop/flow.md` com exatamente este conteúdo:

```markdown
# shop — Fluxo

## Visão geral
Loja online com web, mobile e backoffice.

## Componentes
- **Cliente web** (React) — navegador do cliente.
- **App mobile** (Kotlin) — aplicativo do cliente.
- **Admin backoffice** (React) — equipe interna cadastra produtos e usuários.
- **API Gateway** (Go) — porta de entrada de web e mobile.
- **Auth Service** (Kotlin) — login e tokens.
- **Order Service** (Kotlin) — pedidos.
- **Catalog Service** (Python) — catálogo de produtos.
- **Payment Service** (Kotlin) — cobrança.
- **Notification Worker** (Go) — envia e-mails de pedido.
- **Postgres** — banco de pedidos.
- **Redis** — cache do catálogo.
- **Kafka** — eventos de pedido.

## Integrações externas
- **Gateway de pagamento** — processa cartões. O Payment Service chama via HTTPS.

## Fluxos principais
### Criar pedido
1. Web e mobile chamam o API Gateway.
2. O Gateway chama Auth Service e Order Service.
3. Order Service grava no Postgres, publica no Kafka e chama o Payment Service.
4. Payment Service chama o Gateway de pagamento.
5. Notification Worker consome o Kafka.
6. Catalog Service lê e escreve no Redis. O Gateway chama o Catalog Service.
7. O Admin backoffice chama o Catalog Service (CRUD de produtos) e o Auth Service (usuários).

## Infra e deploy
Nada encontrado.

## Lacunas e dúvidas
- Nenhuma.
```

Depois gere o diagrama de arquitetura em draw.io em `docs/diagrams/shop/architecture-shop.drawio`, a partir das seções Componentes e Integrações externas.
