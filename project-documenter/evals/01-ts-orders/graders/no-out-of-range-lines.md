---
type: regex
match: not_contains
target: {source: file, path: docs/diagrams/orders/flow.md}
---
routes\.ts:(1[5-9]|[2-9]\d|\d{3,})|routes\.ts:\d+-(1[5-9]|[2-9]\d|\d{3,})
