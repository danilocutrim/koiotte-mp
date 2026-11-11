---
type: regex
match: contains
target: {source: file, path: docs/diagrams/orders/infra-orders.drawio}
---
(?=[\s\S]*ALB)(?=[\s\S]*ECS)(?=[\s\S]*RDS)(?=[\s\S]*SQS)(?=[\s\S]*S3)(?=[\s\S]*VPC)
