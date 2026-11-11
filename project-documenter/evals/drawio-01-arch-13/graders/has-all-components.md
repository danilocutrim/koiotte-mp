---
type: regex
match: contains
target: {source: file, path: docs/diagrams/shop/architecture-shop.drawio}
---
(?=[\s\S]*Cliente web)(?=[\s\S]*App mobile)(?=[\s\S]*Admin)(?=[\s\S]*API Gateway)(?=[\s\S]*Auth)(?=[\s\S]*Order)(?=[\s\S]*Catalog)(?=[\s\S]*Payment)(?=[\s\S]*Notification)(?=[\s\S]*Postgres)(?=[\s\S]*Redis)(?=[\s\S]*Kafka)
