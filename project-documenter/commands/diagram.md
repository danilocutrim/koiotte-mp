---
description: Documenta o projeto com diagramas Mermaid ou draw.io. Pergunta o escopo, analisa o código, escreve o flow.md para você aprovar e gera os diagramas. Use /diagram update para atualizar os existentes.
argument-hint: "[update]"
allowed-tools: Read, Glob, Grep, Write, Bash, Task, AskUserQuestion, Skill
---

Argumentos: `$ARGUMENTS`

Se `$ARGUMENTS` for `update`, vá para **Modo update** no final. Caso contrário, siga o fluxo abaixo na ordem, sem pular os gates.

## 1. Perguntas (uma por vez, com AskUserQuestion quando houver opções)
1. **Escopo:** repositório inteiro, ou um serviço/módulo? Se o repositório tiver vários serviços (monorepo: vários manifestos em subpastas), **não aceite "tudo"**: peça para escolher um escopo.
2. **Foco:** qual parte ou fluxo importa mais (ex.: "criação de pedido") ou "visão geral".
3. **Público:** time técnico, novos devs, ou cliente/negócio.

Defina `SCOPE_NAME` (kebab-case, ex.: `order-service`) e `DIR=docs/diagrams/<SCOPE_NAME>`.

## 2. Análise
Se `<DIR>/flow.md` já existir, **antes de qualquer coisa** copie para `<DIR>/flow.md.prev` (`cp`) e avise o usuário que o `flow.md` aprovado antes (inclusive correções manuais) será reescrito; pergunte se quer continuar. Depois da análise, mostre o diff (`diff <DIR>/flow.md.prev <DIR>/flow.md`) no gate do passo 3 e ofereça restaurar a cópia.

Dispare o agent `project-analyst` (Task) com este prompt:
`ESCOPO=<caminho> FOCO=<foco> PUBLICO=<publico> SAIDA=<DIR>/flow.md`
Receba só o resumo curto. Não releia o código analisado.

## 3. Gate: flow.md
Mostre ao usuário o resumo e o caminho do `<DIR>/flow.md`. Peça para ele ler e dizer se aprova ou o que corrigir (ele pode editar o arquivo à mão). Ajustes pedidos: edite o `flow.md` (ou rode o analyst de novo com o feedback). **Só avance com aprovação explícita.**

## 4. Tipo e formato
Pergunte quais tipos gerar (vários permitidos): arquitetura, sequência, fluxo/processo, infra/deploy, caminho da requisição. Para cada tipo, proponha o formato padrão e deixe o usuário trocar (exceto caminho da requisição, que é só drawio: o Mermaid não fixa as colunas):

| Tipo | Seção de origem | Formato padrão |
|---|---|---|
| sequência | Fluxos principais (um `###` por fluxo) | mermaid |
| fluxo e processo | Fluxos principais | mermaid |
| arquitetura | Componentes + Integrações externas | drawio |
| infra e deploy | Infra e deploy + Componentes | drawio |
| caminho da requisição | Fluxos principais (um `###`) + Componentes | drawio |

Para sequência, fluxo e caminho da requisição, pergunte qual fluxo (`###`) quando houver mais de um. Só ofereça caminho da requisição quando um fluxo passar por um hub com etapas (gateway, proxy, cadeia de filtros ou middlewares) e se abrir para 2 ou mais backends.

**Nome do arquivo:** `<slug>-<nome>.<ext>`, com o slug fixo do tipo e o nome em kebab-case ASCII, sem espaços: `sequence-` (sequência), `flow-` (fluxo e processo), `architecture-` (arquitetura), `infra-` (infra e deploy), `request-` (caminho da requisição). Ex.: `sequence-criar-pedido.mmd`, `architecture-shop.drawio`. A extensão é `.mmd` para mermaid e `.drawio` para drawio.

Seção cujo conteúdo é só `Nada encontrado.` (ex.: projeto sem código): **não ofereça** os tipos que dependem dela; explique o motivo e sugira corrigir o `flow.md` ou escolher outro escopo.

## 5. Geração
Para cada diagrama, invoque a skill do formato (`mermaid` ou `drawio`) passando: **todas** as seções de origem da tabela (o texto delas, para o diagrama refletir tudo que o índice vai vigiar), o tipo e o arquivo de destino `<DIR>/<slug>-<nome>.<mmd|drawio>`.
- Se o arquivo de destino já existir, **primeiro** rode `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/index_tool.py" check "<DIR>"` e diga ao usuário o estado dele (`ok`, `desatualizado` ou `editado-à-mão`); só então pergunte se pode sobrescrever, avisando que as edições manuais serão perdidas quando for `editado-à-mão`.
- `.drawio`: a skill valida com `validate_drawio.py`; só considere pronto com `OK`.
- `.mmd`: informe se foi validado com `mmdc` ou **não** foi validado.

## 6. Índice
Para cada diagrama gerado e aceito pelo usuário, registre:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/index_tool.py" add "<DIR>" "<arquivo>" "<tipo>" "<formato>" "<seção de origem>"
```
A origem usa os títulos exatos do `flow.md`, exatamente como na tabela do passo 4 (várias seções unidas por ` + `): `Componentes + Integrações externas`, `Infra e deploy + Componentes`, `Fluxos principais › <nome do fluxo>` ou `Fluxos principais › <nome do fluxo> + Componentes`. Erro do script: corrija a origem e repita; nunca edite o `INDEX.md` à mão.

Termine listando os arquivos criados.

## Modo update
1. Pergunte o escopo (ou liste as pastas em `docs/diagrams/` que têm `INDEX.md`).
2. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/index_tool.py" check "<DIR>"`. Saída `sem INDEX.md`: avise e ofereça o fluxo normal.
3. Se o código mudou, ofereça rodar o `project-analyst` de novo: ele reescreve o `flow.md`; mostre o que mudou e passe pelo **gate do passo 3**.
4. Rode `check` de novo e mostre a tabela com o estado de cada diagrama: `ok`, `desatualizado`, `editado-à-mão`, `origem-removida`, `arquivo-ausente`.
5. Pergunte quais regenerar. **Diagrama com `editado-à-mão` só é regenerado com confirmação explícita para aquele arquivo**, avisando que as edições manuais serão perdidas. `origem-removida`: pergunte se apaga o diagrama ou escolhe outra origem.
6. Regenere pelo passo 5 e registre pelo passo 6.
