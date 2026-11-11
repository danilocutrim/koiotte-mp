---
type: regex
match: contains
target: {source: file, path: docs/diagrams/mega/architecture-mega.drawio}
---
(?=[\s\S]*billing-api)(?=[\s\S]*catalog-api)(?=[\s\S]*shipping-api)(?=[\s\S]*image-bucket)(?=[\s\S]*tracking-worker)
