---
type: llm
focus: {source: file, path: docs/diagrams/payments/flow.md}
---
Passa somente se TODOS os itens da seção "Componentes" trazem uma citação no formato arquivo:número (ex.: OrderController.kt:5 ou build.gradle.kts:2) e os arquivos citados são apenas build.gradle.kts ou src/main/kotlin/OrderController.kt. Falha se algum componente não tem citação com número de linha, ou cita arquivo que não foi criado.
