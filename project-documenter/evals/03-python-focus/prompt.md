---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Agent]
runs: 3
---
Crie estes 2 arquivos no diretório atual, exatamente com este conteúdo.

`pyproject.toml`:
```toml
[project]
name = "shop-api"
dependencies = ["fastapi", "uvicorn", "boto3"]
```

`app/main.py`:
```python
from fastapi import FastAPI
import boto3

app = FastAPI()
users = boto3.resource("dynamodb").Table("users")
orders = boto3.client("sqs")

@app.post("/login")
def login(body: dict):
    user = users.get_item(Key={"email": body["email"]}).get("Item")
    if not user or user["password"] != body["password"]:
        return {"error": "invalid credentials"}
    return {"token": "t-" + user["email"]}

@app.post("/orders")
def create_order(body: dict):
    orders.send_message(QueueUrl="orders-queue", MessageBody=str(body))
    return {"status": "queued"}
```

Depois analise o código e documente em `docs/diagrams/auth/flow.md`, em linguagem natural, SOMENTE o fluxo de login. Cite os arquivos de onde tirou cada informação e deixe explícito o que não dá para saber só pelo código.
