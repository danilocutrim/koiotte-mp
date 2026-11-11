---
name: mermaid
description: Gera diagramas Mermaid (.mmd ou bloco em markdown) de sequência, fluxo/processo e arquitetura simples. Use quando o usuário pedir um diagrama Mermaid, ou quando o /diagram escolher Mermaid.
---

# Mermaid

## Entrada e saída
- Entrada: uma seção do `flow.md` (ou uma descrição direta do usuário) e o tipo de diagrama.
- Saída: `.mmd` com o diagrama puro. Se o destino for um `.md`, use um bloco ```mermaid.
- Nome do arquivo: `<tipo>-<nome-em-kebab>.mmd` (ex.: `sequence-criar-pedido.mmd`).

## Qual referência ler (leia só a necessária)
- Sequência entre serviços ou módulos → `references/sequence.md`
- Fluxo, processo, regras, estados → `references/flow.md`
- Arquitetura simples (componentes e dependências) → `references/architecture.md`
- Infra AWS com ícones ou arquitetura densa: Mermaid é fraco aqui. Diga isso ao usuário e sugira a skill `drawio`. Se ele insistir, use `references/architecture.md` e avise das limitações.

## Regras gerais
1. No máximo ~15 nós por diagrama. Passou disso, divida em subgrafos ou em vários diagramas.
2. IDs de nós estáveis e em ASCII (`orderSvc`, `ordersQueue`); o texto legível vai no rótulo. Isso mantém o diff do git limpo.
3. Rótulos com caracteres especiais (`()`, `:`, `/`) vão entre aspas: `A["POST /orders"]`.
4. Todo elemento do diagrama vem do `flow.md`. Não invente componentes. Itens `[inferido]` aparecem com `?` no rótulo ou em nota.
5. Um diagrama por arquivo.

## Validação
- Se `mmdc` existir (`command -v mmdc`): `mmdc -i arquivo.mmd -o /tmp/check.svg` e relate o resultado.
- Se não existir: diga explicitamente que a sintaxe **não foi validada** automaticamente. Nunca afirme que validou sem ter rodado.
