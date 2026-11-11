---
type: llm
focus: {source: file, path: docs/diagrams/shop/flow-fechar-pedido.mmd}
---
O fluxo original tem 18 passos e 3 decisões com saída de rejeição. Passa somente se (a) este arquivo NÃO tem mais de cerca de 15 nós no mesmo diagrama sem agrupá-los em subgraph, OU o diagrama foi dividido e este arquivo é só a parte principal com os nós restantes agrupados; e (b) toda decisão (losango/chaves) tem todas as suas saídas rotuladas (por exemplo sim/não). Falha se há um único diagrama plano com mais de ~15 nós, ou uma decisão com saída sem rótulo.
