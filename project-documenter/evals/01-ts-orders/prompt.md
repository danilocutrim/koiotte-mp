---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Agent]
runs: 3
---
Crie estes 3 arquivos no diretório atual, exatamente com este conteúdo.

`package.json`:
```json
{ "name": "orders-api", "version": "1.0.0", "dependencies": { "express": "^4.19.0", "@aws-sdk/client-sqs": "^3.0.0" } }
```

`src/routes.ts`:
```ts
import express from "express";
import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";

const app = express();
const sqs = new SQSClient({ region: "us-east-1" });

app.post("/orders", async (req, res) => {
  const order = { id: Date.now(), ...req.body };
  await sqs.send(new SendMessageCommand({ QueueUrl: process.env.ORDERS_QUEUE_URL!, MessageBody: JSON.stringify(order) }));
  res.status(202).json(order);
});

app.get("/orders/:id", (req, res) => res.json({ id: req.params.id }));
```

`infra/sqs.tf`:
```hcl
resource "aws_sqs_queue" "orders" {
  name = "orders-queue"
}
```

Depois analise esse código e documente em `docs/diagrams/orders/flow.md`, em linguagem natural, como o serviço funciona: componentes, fluxos, integrações e infra. Cite os arquivos de onde tirou cada informação e deixe explícito o que não dá para saber só pelo código.
