---
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Skill, "Bash(python3 \"/home/danilo/Workspace/project-documenter/scripts/validate_drawio.py\":*)"]
runs: 3
---
Crie `docs/diagrams/orders/flow.md` com exatamente este conteúdo:

```markdown
# orders — Fluxo

## Visão geral
Serviço de pedidos na AWS.

## Componentes
- **orders-svc** (ECS) — API de pedidos. `infra/ecs.tf:1`
- **orders-db** (RDS Postgres) — banco. `infra/rds.tf:1`
- **orders-queue** (SQS) — fila de pedidos. `infra/sqs.tf:1`
- **orders-exports** (S3) — bucket de exportações. `infra/s3.tf:1`
- **orders-alb** (ALB) — balanceador público. `infra/alb.tf:1`

## Fluxos principais
### Criar pedido
1. O ALB encaminha para o orders-svc.
2. O orders-svc grava no orders-db, publica no orders-queue e grava exportações no orders-exports.

## Integrações externas
Nada encontrado.

## Infra e deploy
Conta AWS única, região us-east-1. Uma VPC com subnet pública (o ALB) e subnet privada (orders-svc e orders-db). SQS e S3 ficam na região, fora da VPC. `infra/vpc.tf:1-30`

## Lacunas e dúvidas
- Pipeline de deploy não encontrado.
```

Depois gere o diagrama de infra e deploy em draw.io em `docs/diagrams/orders/infra-orders.drawio`, a partir das seções Infra e deploy e Componentes.
