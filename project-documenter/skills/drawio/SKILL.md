---
name: drawio
description: Gera arquivos draw.io (.drawio, XML mxGraph) de arquitetura, infra/deploy (incluindo AWS) e caminho da requisição por um gateway ou proxy. Use quando o usuário pedir draw.io, diagrama AWS ou arquitetura visual, ou quando o /diagram escolher draw.io.
---

# draw.io

## Entrada e saída
- Entrada: seção do `flow.md` (Componentes, Integrações externas ou Infra e deploy) e o tipo.
- Saída: `<tipo>-<nome-em-kebab>.drawio`, XML escrito direto (sem ferramenta externa).

## Qual referência ler
- **Sempre** `references/layout.md`: como posicionar os nós e prever a rota das setas. É o que separa um diagrama legível de um emaranhado.
- Arquitetura de componentes, serviços e dependências → `references/architecture.md`
- Infra e deploy na AWS (contas, regiões, VPC, subnets, serviços) → `references/infra-aws.md`
- Caminho da requisição (um fluxo atravessando as etapas de um hub até vários backends, em colunas) → `references/request-path.md`. Esse tipo troca algumas regras abaixo: os contêineres são retângulos com `container=1` (não `swimlane`), pílulas de 30 px de altura, detalhe de código visível em monoespaçado e portas explícitas nas setas. A referência diz exatamente o quê, e o molde é `${CLAUDE_PLUGIN_ROOT}/skills/drawio/references/request-path-sample.drawio`.

## Estrutura mínima do arquivo
Uma `mxCell` por linha. O arquivo completo e válido, com contêiner, tooltip e setas, está em `${CLAUDE_PLUGIN_ROOT}/skills/drawio/references/sample.drawio` (use como molde).
```xml
<mxfile host="app.diagrams.net">
  <diagram name="NOME" id="d1">
    <mxGraphModel grid="1" gridSize="10" page="1" pageWidth="1100" pageHeight="700">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Regras de geração (o procedimento completo está em `references/layout.md`)
1. **IDs únicos e estáveis** (`orderSvc`, `e-orderSvc-ordersQueue`), nunca números aleatórios.
2. **Camadas, com o hub no centro.** Sistema com um ponto de entrada e vários atores e serviços: camadas de cima para baixo (atores, entrada, serviços, dados e filas, workers e externos). Pipeline: da esquerda para a direita. Nós ligados ficam em camadas vizinhas.
3. **Corredor livre entre camadas.** Nenhum nó pode ficar no caminho de uma seta entre outros dois. Antes de escrever cada seta, imagine a rota que o draw.io vai tomar (regra em `layout.md`); se ela passar por cima de um terceiro nó, reordene ou aproxime os nós.
4. **Contêineres de verdade.** Grupos (serviço, VPC, região) são `swimlane` com `startSize=24`. Os filhos usam `parent="<id do contêiner>"` e **coordenadas relativas** ao contêiner. Setas entre contêineres diferentes, ou entre um nó de fora e um de dentro, usam `parent="1"`. Nunca desenhe um retângulo e ponha os nós por cima dele.
5. **Tamanho do nó pelo texto:** largura = `max(120, 8 × maior linha)` arredondada para 10; altura = `20 + 18 × nº de linhas`, mínimo 60. Rótulo com no máximo **3 linhas** de ~22 caracteres. Detalhes longos (portas, classes, listas) vão para o atributo `tooltip`.
6. **Setas:** `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;`. Cada seta que sai do mesmo nó tem **rótulo próprio** (curto, até ~20 caracteres). Agregue fan-outs do mesmo protocolo em uma seta rotulada. Assíncrono é tracejado (`dashed=1`).
7. **Formato:** posições e tamanhos em múltiplos de 10 (grade de 10), `html=1` nos estilos, uma `mxCell` por linha.
8. **Fidelidade:** todo elemento vem do `flow.md`. Itens `[inferido]` recebem rótulo com `?`. Não invente componentes. Ícone cujo nome você não tem certeza: retângulo com a cor da categoria. Nunca invente nome de ícone.
9. **Tamanho:** mais de ~20 elementos por página: uma página (`<diagram>`) por domínio, mais uma de visão geral.

## Validação e renderização (obrigatórias, nesta ordem)
**1. Validador:**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_drawio.py" caminho/arquivo.drawio
```
- **erro** (exit 1): estrutura inválida, ou uma seta que **atravessa** um nó que não é origem nem destino. Reordene os nós e rode de novo.
- **aviso** (`aviso: ...`): rota provável cortando um nó, texto que não cabe, rótulos repetidos saindo do mesmo nó, nó dentro de um grupo sem ser filho dele, ou fora da grade. Corrija o que for evitável e rode de novo.

**2. Rota exata das setas.** Se `command -v drawio` existir, o verificador renderiza o diagrama e lê o caminho **real** de cada seta (sem adivinhar):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/route_check.py" caminho/arquivo.drawio
```
- **erro** (exit 1): uma seta **passa por dentro** de um nó que não é origem nem destino. Reordene os nós ou aproxime os ligados e rode de novo.
- **aviso**: cruzamentos entre setas. Reduza reordenando as camadas; sobrando 1 ou 2 em diagramas densos é aceitável.
- exit 3 (`não foi renderizado`): o CLI não existe ou falhou; siga para o passo 3 e diga que a rota real não foi verificada.
(abre o draw.io por alguns segundos; erros de GPU no log são ruído.)

**3. Olhar o resultado.** Gere um PNG temporário e olhe-o com a ferramenta Read:
```bash
drawio -x -f png -s 1 -o /tmp/diagrama-check.png caminho/arquivo.drawio
```
Procure: rótulos sobrepostos ou cortados, texto estourando a caixa, setas coladas no mesmo tronco. Corrija e repita os passos 2 e 3, no máximo **2 rodadas**. Não deixe o PNG dentro do projeto, a menos que o usuário peça. Se o CLI não existir, diga que o diagrama **não foi renderizado**.

Só entregue com o validador em `OK`, sem seta por dentro de nó e sem avisos evitáveis. Se sobrar algum, diga qual. O validador prevê a rota por heurística (e já errou); o `route_check.py` e a renderização é que confirmam.

## Export (opcional)
Se o usuário pedir PNG, SVG ou PDF e o CLI existir: `drawio -x -f png -o saida.png arquivo.drawio`. Sem o CLI, entregue só o `.drawio` e diga que o export não foi feito.

## Limite
O layout calculado é um ponto de partida; o usuário pode ajustar no draw.io. Avise que edição manual impede a regeneração automática sem confirmação.
