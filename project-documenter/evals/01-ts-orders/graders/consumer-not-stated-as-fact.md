---
type: llm
focus: {source: file, path: docs/diagrams/orders/flow.md}
---
O código só publica mensagens em orders-queue; nenhum consumidor existe nos arquivos. Passa se o documento NÃO afirma como fato quem consome a fila (nem nomeia um worker ou serviço consumidor) e, em vez disso, marca o consumidor como [inferido] ou o lista em lacunas/dúvidas. Falha se afirma um consumidor concreto sem ressalva.
