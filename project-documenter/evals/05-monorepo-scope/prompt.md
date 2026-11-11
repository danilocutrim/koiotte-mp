---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Agent]
runs: 3
---
Crie estes 4 arquivos no diretório atual (um monorepo com dois serviços), exatamente com este conteúdo.

`billing/go.mod`:
```
module example.com/billing

go 1.22
```

`billing/main.go`:
```go
package main

import "net/http"

func main() {
	http.HandleFunc("/invoices", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("[]"))
	})
	http.ListenAndServe(":8080", nil)
}
```

`catalog/package.json`:
```json
{ "name": "catalog-service", "dependencies": { "express": "^4.19.0" } }
```

`catalog/src/index.ts`:
```ts
import express from "express";
const app = express();
app.get("/products", (_req, res) => res.json([]));
app.listen(3000);
```

Depois analise SOMENTE o serviço `billing/` e documente em `docs/diagrams/billing/flow.md`, em linguagem natural, como ele funciona: componentes, fluxos, integrações e infra. Cite os arquivos de onde tirou cada informação e deixe explícito o que não dá para saber só pelo código.
