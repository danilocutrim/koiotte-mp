# project-documenter — Design

Data: 2026-10-02 · Status: aguardando revisão

## Objetivo

Plugin do Claude Code que ajuda a documentar projetos criando diagramas **Mermaid** e **draw.io**. Ele entende o projeto lendo o código, descreve o fluxo em linguagem natural para o usuário validar e só então gera os diagramas.

**Usos:** (1) documentação viva no repositório, com Mermaid e `.drawio` versionados no git; (2) entregas mais elaboradas em draw.io, com export opcional.
**Stacks alvo:** Kotlin, Go, Python, TypeScript, AWS.
**Tipos na v1:** arquitetura, sequência, fluxo e processo, infra e deploy.
**Referência:** `drawio-skill` da Agents365-ai (para inspiração, não como dependência).

## Fora do escopo da v1

ER, diagramas de classe, Gantt, hooks que atualizam diagramas a cada commit e geração de imagem sem CLI instalado.

## Estrutura

```
project-documenter/
├── .claude-plugin/plugin.json
├── commands/diagram.md            # orquestrador: perguntas, gates, escolha de tipo e formato
├── agents/project-analyst.md      # análise do código em contexto isolado, com "onde olhar" por stack
└── skills/
    ├── mermaid/
    │   ├── SKILL.md
    │   └── references/  sequence.md  flow.md  architecture.md
    └── drawio/
        ├── SKILL.md
        └── references/  architecture.md  infra-aws.md
```

**Por que essa divisão**
- O **command** fica com o diálogo, porque subagentes não conversam com o usuário no meio da execução.
- O **agent** isola a leitura pesada de código e devolve só um resumo curto.
- **Uma skill por formato** permite disparo independente ("faz um mermaid") e mantém a sintaxe, os limites e o export de cada formato juntos. O corpo e os `references/` só carregam sob demanda.

## Fluxo do `/diagram`

1. **Perguntas** (uma por vez): escopo (repo, serviço ou módulo), foco e público.
2. **Análise:** o `project-analyst` varre o código e devolve um resumo curto (componentes, lacunas, dúvidas).
3. **Documento de fluxo:** escreve `docs/diagrams/<escopo>/flow.md`. **Gate:** o usuário lê, corrige e aprova.
4. **Tipo e formato:** o usuário escolhe o tipo, e o command sugere o formato padrão (Mermaid para sequência e fluxo, draw.io para arquitetura e infra). O usuário pode sobrescrever.
5. **Geração:** a skill do formato carrega os `references/` necessários e escreve `docs/diagrams/<escopo>/<tipo>-<nome>.mmd` ou `.drawio`.
6. **Índice:** atualiza `docs/diagrams/<escopo>/INDEX.md`.

**Monorepo:** o passo 1 sempre fixa um escopo, e o plugin nunca analisa o monorepo inteiro de uma vez.

## `project-analyst`

- **Entrada:** escopo, foco e público.
- **Detecção de stack** por manifestos: `build.gradle.kts`, `go.mod`, `pyproject.toml`, `package.json`, `*.tf`, `template.yaml`, `serverless.yml`, `cdk.json`.
- **Pistas:** rotas, handlers, controllers, consumers de fila, OpenAPI; clientes HTTP e gRPC, filas, tópicos, buckets, tabelas; Terraform, CDK, CloudFormation, Dockerfiles.
- **Saída:** escreve o `flow.md` e devolve ao command um resumo de poucas linhas.
- **Honestidade:** cada afirmação cita a origem (`arquivo:linha`). O que foi inferido e não verificado leva `[inferido]`. O que não foi encontrado vai em "Lacunas".
- **Ferramentas:** só leitura (Read, Grep, Glob) e escrita do `flow.md`. Não executa o código do projeto.

## Formato do `flow.md`

Seções: Visão geral · Componentes · Fluxos principais · Integrações externas · Infra e deploy · Lacunas e dúvidas.

| Tipo de diagrama | Seção de origem |
|---|---|
| Arquitetura | Componentes |
| Sequência | Fluxos principais |
| Fluxo e processo | Fluxos principais e regras |
| Infra e deploy | Infra e deploy |

## Skill `mermaid`

- **Cobre:** `sequenceDiagram`, `flowchart`, `stateDiagram` e arquitetura simples.
- **Saída:** `.mmd` puro, ou bloco ```mermaid embutido quando o destino é um `.md`.
- **Regras:** no máximo uns 15 nós por diagrama (acima disso, subgrafos ou vários diagramas); IDs de nós estáveis para diffs limpos.
- **Validação:** usa `mmdc` se estiver instalado. Se não estiver, avisa que não validou.

## Skill `drawio`

- **Cobre:** arquitetura e infra AWS (biblioteca `mxgraph.aws4`, grupos de conta, região, VPC e subnets, setas rotuladas, layout em grade com coordenadas calculadas).
- **Saída:** `.drawio` em XML mxGraph escrito direto, sem dependência externa.
- **Validação:** XML bem formado, IDs únicos, arestas apontando para nós existentes.
- **Export:** PNG, SVG ou PDF só se o CLI do draw.io estiver instalado. Caso contrário, entrega só o `.drawio`.
- **Limite:** o layout automático não substitui um ajuste visual manual. O arquivo é pensado para ser editado depois.

## `INDEX.md` e atualização

Colunas: Diagrama · Tipo · Formato · Origem no `flow.md` · Gerado em · Hash origem · Hash arquivo (o hash do arquivo detecta edição à mão).

- `/diagram update` compara os hashes, lista os diagramas desatualizados e pergunta quais regenerar.
- Diagrama editado à mão depois de gerado (detectado por data e conteúdo) **nunca é sobrescrito sem perguntar**.
- Mudança no código sem mudança no `flow.md`: o update pode rodar o analyst de novo, mostrar o diff do `flow.md` e passar pelo mesmo gate.

## Decisões em aberto

Nenhuma bloqueante. Defaults assumidos e aprovados: tudo em `docs/diagrams/`, escopo por serviço em monorepo, export opcional, formato padrão por tipo sobrescrevível.

## Testes e validação

- Plugin sem código de aplicação: a verificação é por **projetos de exemplo** (um por stack, mínimos) rodando `/diagram` de ponta a ponta.
- Validadores determinísticos para saída: XML do `.drawio` e `mmdc` para `.mmd`, quando disponíveis.
- Casos a cobrir: projeto sem infra, monorepo, `flow.md` com muitas lacunas, diagrama editado à mão no update.
