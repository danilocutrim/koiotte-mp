---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Skill]
runs: 3
---
Preciso de um diagrama de infraestrutura AWS em Mermaid, salvo em `docs/diagrams/infra/infra-aws.mmd`: uma VPC com subnet pública (ALB) e subnet privada (ECS e RDS), mais uma fila SQS e um bucket S3 fora da VPC.
