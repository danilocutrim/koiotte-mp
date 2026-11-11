# Arquitetura em draw.io

Fonte no `flow.md`: **Componentes** e **Integrações externas**. Leia antes `references/layout.md`.

## Passo a passo
1. Liste os componentes, o ponto de entrada (hub) e quem chama quem.
2. Agrupe por fronteira (serviço, domínio) em contêineres `swimlane` de verdade (veja `layout.md`, seção 7).
3. Monte as camadas: atores, entrada, serviços, dados e filas, workers e externos. Nós ligados em camadas vizinhas.
4. Ordene cada camada para **minimizar cruzamentos** (baricentro, `layout.md` seção 3): o ator fica acima do serviço que ele mais chama.
5. Crie uma seta por dependência do `flow.md`, com rótulo próprio e curto. Antes de escrevê-la, preveja a rota; se ela cortar um nó, reordene.

## Estilos (copie exatamente)
- Serviço: `rounded=1;whiteSpace=wrap;html=1;fillColor=#ED7100;fontColor=#ffffff;strokeColor=none;`
- Banco de dados: `shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#C925D1;fontColor=#ffffff;strokeColor=none;`
- Fila ou evento: `rounded=1;whiteSpace=wrap;html=1;fillColor=#E7157B;fontColor=#ffffff;strokeColor=none;`
- Ator ou cliente: `rounded=1;whiteSpace=wrap;html=1;fillColor=#1b2a41;fontColor=#ffffff;strokeColor=#5b7db1;`
- Externo ao sistema: `rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;dashed=1;`
- Contêiner: `swimlane;startSize=24;html=1;fillColor=none;dashed=1;strokeColor=#147EBA;fontStyle=1;`
- Seta síncrona: `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;` · assíncrona: o mesmo com `dashed=1;`

## Dimensionamento (evita texto estourando a caixa)
- Largura = `max(120, 8 × maior linha)` (arredonde para 10); altura = `20 + 18 × linhas`, mínimo 60.
- Rótulo com até 3 linhas de ~22 caracteres. `Management Plane` + `(Go, Control API :8080)` cabe em 2 linhas; uma lista de 3 classes não cabe: ponha a lista no `tooltip`.
- Título de contêiner curto (`app/ (Kotlin)`), nunca a lista de tecnologias.

## Limite de tamanho
Mais de ~20 elementos por página: uma página (`<diagram>`) por domínio e uma de visão geral.
