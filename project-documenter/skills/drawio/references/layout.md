# Como posicionar os nós e prever a rota das setas

A maior parte do que torna um diagrama ruim vem de duas coisas: nós colocados sem pensar em quem fala com quem, e setas que o draw.io roteia por cima de outros nós. Este procedimento evita as duas. Vale para qualquer diagrama.

## 1. Escolha a direção
- Um **hub** (gateway, barramento) com vários atores e serviços: camadas **de cima para baixo**.
- Um pipeline ou uma sequência de etapas (CI/CD, ETL): da esquerda para a direita.

## 2. Monte as camadas
Cada nó vai em exatamente uma camada (todos com o mesmo `y` numa descida, ou o mesmo `x` num pipeline). Para um sistema típico:

1. atores (clientes, admin)
2. entrada (gateway, balanceador), com o **hub no centro** da camada dele
3. serviços
4. dados e filas
5. workers e sistemas externos

Nós ligados por uma seta ficam em **camadas vizinhas**. Uma seta que pula uma camada é a causa clássica de cruzamento.

## 3. Ordene dentro da camada (baricentro)
Para cada nó, calcule a média da posição (1, 2, 3...) dos vizinhos dele na camada anterior, e ordene a camada por essa média. Repita de cima para baixo e de baixo para cima, duas vezes. Na prática: o ator fica **acima do serviço que ele mais chama**, e atores que chamam o mesmo serviço ficam lado a lado.

## 4. Coordenadas
- Passo horizontal = largura do maior nó + 80; corredor vertical entre camadas de **pelo menos 100 px**.
- Tudo em múltiplos de 10 (grade de 10); nós da mesma camada alinhados pelo centro.
- Tamanho do nó pelo texto: largura `max(120, 8 × maior linha)`, altura `20 + 18 × linhas`, mínimo 60; no máximo 3 linhas de ~22 caracteres; detalhes no `tooltip`.

## 5. Confira a rota de cada seta
Com `edgeStyle=orthogonalEdgeStyle` e sem waypoints, o draw.io escolhe o caminho assim (padrão observado em diagramas reais):

| Posição das caixas | Rota |
|---|---|
| Se sobrepõem na horizontal (uma acima da outra) | sai pela vertical, anda na horizontal no meio do espaço entre elas, entra pela vertical |
| Se sobrepõem na vertical (lado a lado) | sai pela horizontal, anda na vertical no meio, entra pela horizontal |
| Não se sobrepõem em nenhum eixo (em diagonal) | **horizontal primeiro**, depois vertical até o destino |

Desenhe o caminho de cada seta na cabeça. Se ele passar por cima de um terceiro nó, **reordene**, aproxime os dois nós (mesma coluna, ou camada vizinha) ou, como último recurso, use um waypoint (`<Array as="points">`). Exemplo do erro típico: o gateway à esquerda, e o catálogo no alto da coluna da direita com outros serviços abaixo dele; a seta em diagonal sai na horizontal, depois sobe pela coluna e **atravessa** os serviços do meio.

## 6. Setas e rótulos
- Estilo base: `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;`.
- Cada seta que sai do mesmo nó tem **rótulo próprio**: "Route, Route, Route" vira "serviço A, serviço B, serviço C".
- Quando um nó chama vários destinos da mesma camada com o mesmo protocolo, **agregue** tudo em uma seta rotulada ("HTTP → serviços").
- Quando duas setas dividem um trecho e os rótulos colidem, desloque o **rótulo**, não a seta: `<mxGeometry relative="1" x="-0.3" y="-12" as="geometry"/>` (`x` anda ao longo da seta, de -1 a 1; `y` afasta dela).
- Rótulos de até ~20 caracteres. No máximo 2 setas de observabilidade (logs e métricas) no diagrama inteiro.
- Assíncrono é tracejado (`dashed=1`).

## 7. Contêineres de verdade
- Cada grupo é um `swimlane` com `startSize=24` (faixa de título), título curto (até ~25 caracteres).
- Filhos: `parent="<id do contêiner>"`, coordenadas **relativas** ao canto do contêiner, com `y` de pelo menos 24 + 30 de margem, e 30 px de margem nos lados.
- Setas entre contêineres diferentes, ou entre um nó de fora e um de dentro, têm `parent="1"`; senão ficam presas dentro do contêiner e são cortadas.
- Setas que atravessam a borda de um contêiner são normais. Não contorne o contêiner com waypoints.
- Nunca desenhe um retângulo grande e coloque os nós por cima dele com `parent="1"`: o validador acusa, e o grupo não move junto.

## 8. Antes de entregar
- [ ] Cada nó numa camada; conectados em camadas vizinhas; hub no centro.
- [ ] Nenhuma rota prevista passa por cima de um terceiro nó.
- [ ] Rótulo próprio em cada seta que sai do mesmo nó; fan-outs agregados.
- [ ] Texto cabe (até 3 linhas), detalhe no `tooltip`.
- [ ] Contêineres são `swimlane` com filhos de verdade; setas entre contêineres em `parent="1"`.
- [ ] Múltiplos de 10, `html=1`, uma `mxCell` por linha.
- [ ] Validador em `OK`; PNG renderizado e olhado (se o CLI existir).
