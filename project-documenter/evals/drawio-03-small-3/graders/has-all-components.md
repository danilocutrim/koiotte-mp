---
type: regex
match: contains
target: {source: file, path: docs/diagrams/notes/architecture-notes.drawio}
---
(?=[\s\S]*Frontend)(?=[\s\S]*API)(?=[\s\S]*Postgres)
