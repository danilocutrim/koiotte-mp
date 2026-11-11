---
type: regex
match: contains
target: {source: file, path: docs/diagrams/orders/flow.md}
---
routes\.ts[\s\S]*orders-queue|orders-queue[\s\S]*routes\.ts
