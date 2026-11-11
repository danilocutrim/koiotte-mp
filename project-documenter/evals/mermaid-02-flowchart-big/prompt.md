---
max_turns: 30
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Write, Skill]
runs: 3
---
Crie `docs/diagrams/shop/flow.md` com exatamente este conteúdo:

```markdown
# shop — Fluxo

## Visão geral
Fechamento de pedido.

## Componentes
Nada encontrado.

## Fluxos principais
### Fechar pedido
1. Receber o pedido.
2. Validar os dados do cliente. Se inválidos, rejeitar e terminar.
3. Verificar estoque de cada item. Se faltar item, avisar o cliente e terminar.
4. Reservar o estoque.
5. Calcular frete.
6. Calcular impostos.
7. Aplicar cupom, se houver.
8. Calcular o total.
9. Cobrar o cliente. Se o pagamento for recusado, liberar o estoque e terminar.
10. Registrar o pagamento.
11. Gerar a nota fiscal.
12. Separar os itens no depósito.
13. Embalar.
14. Gerar a etiqueta de envio.
15. Entregar à transportadora.
16. Enviar o código de rastreio ao cliente.
17. Atualizar o status do pedido para "enviado".
18. Encerrar.

## Integrações externas
Nada encontrado.

## Infra e deploy
Nada encontrado.

## Lacunas e dúvidas
- Nenhuma.
```

Depois gere o fluxograma do fluxo "Fechar pedido" em Mermaid em `docs/diagrams/shop/flow-fechar-pedido.mmd`. Se dividir em vários diagramas, o principal fica nesse arquivo e os outros usam o sufixo `-2`, `-3`.
