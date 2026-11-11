---
type: regex
match: not_contains
target: {source: file, path: docs/diagrams/empty/flow.md}
flags: i
---
\b(express|spring|lambda|dynamodb|sqs|postgres|kafka)\b
