---
type: regex
match: contains
flags: i
target: {source: file, path: docs/diagrams/auth/sequence-login.mmd}
---
/login[\s\S]*token
