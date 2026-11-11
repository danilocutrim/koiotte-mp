---
type: regex
match: contains
target: {source: file, path: docs/diagrams/payments/flow.md}
---
OrderController[\s\S]*payments-queue|payments-queue[\s\S]*OrderController
