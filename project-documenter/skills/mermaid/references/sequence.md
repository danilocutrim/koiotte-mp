# Diagramas de sequência

Fonte no `flow.md`: seção **Fluxos principais** (um `###` por fluxo).

## Mapeamento
- Cada ator ou componente citado nos passos vira um `participant`.
- Cada passo numerado vira uma mensagem: `->>` (chamada), `-->>` (resposta), `-)` (assíncrona, fila ou evento).
- Passo condicional vira `alt/else`; repetição vira `loop`; paralelismo vira `par`.

## Exemplo
```mermaid
sequenceDiagram
    participant client as Cliente
    participant orderSvc as order-service
    participant ordersQueue as orders-queue (SQS)
    participant billing as billing-worker
    client->>orderSvc: POST /orders
    orderSvc->>orderSvc: grava pedido (DynamoDB)
    orderSvc-)ordersQueue: publica OrderCreated
    ordersQueue-)billing: entrega mensagem
    billing-->>ordersQueue: ack
```

## Cuidados
- Declare `participant` na ordem em que aparecem no fluxo, da esquerda para a direita.
- Fluxo com mais de ~12 mensagens: divida por fase (`%% fase: cobrança`) ou em dois diagramas.
- Use `Note over A,B:` para marcar `[inferido]`.
