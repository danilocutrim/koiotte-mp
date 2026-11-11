# Caminho da requisição em draw.io

Fonte no `flow.md`: **um** fluxo de `Fluxos principais` (o `###` escolhido) mais **Componentes**, para os nomes e as portas. Leia antes `references/layout.md`; aqui ficam só as regras que mudam.

## O que é e quando usar
Mostra o caminho de **uma** requisição atravessando um hub (gateway, proxy, cadeia de middlewares ou de filtros) até N backends. Ele empilha as etapas de cima para baixo e mantém cada backend numa **coluna fixa**, do roteamento até o destino. É um diagrama em camadas: um meio-termo entre o de componentes (o que existe) e o de sequência (em que ordem).

Use quando o fluxo tiver **etapas dentro do hub** (filtros, autenticação, roteamento, transformação) e **fan-out** para 2 a 5 backends. Sem hub com etapas, o tipo certo é arquitetura; com muitas idas e voltas entre atores, é sequência.

Molde completo e validado: `${CLAUDE_PLUGIN_ROOT}/skills/drawio/references/request-path-sample.drawio`. Copie os estilos dele, não os invente.

## Anatomia (de cima para baixo)
1. **Origem**: caixa centralizada com o ator (negrito), um subtítulo cinza na mesma linha e até 2 linhas monoespaçadas com a requisição real (`POST /orders`, corpo resumido).
2. **Hub**: contêiner grande com o nome em negrito no canto e um detalhe à direita (`listener :443`).
3. **Faixas**: cada etapa do hub é uma faixa da largura toda (900 px), com o rótulo da etapa na **calha** à esquerda (nome em negrito e uma linha de subtítulo) e o conteúdo começando em x = 190 relativo à faixa.
4. **Roteamento**: uma linha de pílulas, uma por rota, cada uma no centro da sua coluna. O caminho que não casa nada vai numa pílula **tracejada** à direita (`o resto → 404`).
5. **Destinos**: uma caixa por backend, fora do hub e na sua coluna, com o nome em negrito e até 3 linhas monoespaçadas (host:porta, endpoints).

## A grade de colunas (o que deixa tudo reto)
- Cada backend tem uma **coluna** com centro fixo. Com o hub em x=20 e as faixas em x=40 (página), use centros em x = 310, 520, 730 (passo de 210). A calha (x < 230) nunca recebe coluna. Para 4 ou 5 colunas, alargue o hub, as faixas e a página em 210 px por coluna extra e empurre a pílula tracejada para a direita.
- **Tudo o que pertence a um backend tem o centro na coluna dele**: a pílula da rota, a caixa por rota dentro de uma faixa e a caixa de destino. Assim toda seta é uma vertical reta, sem cruzamento e sem rota a prever.
- O fan-out acontece **uma vez**, num barramento: setas da faixa anterior (`exitX=0.5;exitY=1`) para o topo de cada pílula (`entryX=0.5;entryY=0`). O draw.io junta as setas num tronco horizontal. Esse é o único trecho compartilhado.
- Seta que entra ou sai de uma faixa larga usa porta explícita na coluna: `entryX = (centro da coluna − x da faixa) / largura da faixa`, com 4 casas (310 → `0.3`, 520 → `0.5333`, 730 → `0.7667` para faixa em x=40 com 900 de largura). Sem a porta, a seta mira o centro da faixa e entorta.

## Cores: neutro e um destaque
- Tudo em cinza-azulado (slate). Texto `#0f172a` (título), `#334155` (corpo), `#64748b` (secundário). Bordas `#94a3b8`. Fundo do hub `#f8fafc` com borda `#cbd5e1`.
- **Uma** cor de destaque (índigo) só para as etapas que são o assunto do diagrama: faixa `#eef2ff`/`#6366f1`, pílula `#e0e7ff`/`#4f46e5` com texto `#312e81`. Nunca mais de um destaque.
- Faixa de infraestrutura (pools, clusters): `#f1f5f9` com borda `#94a3b8`.

## Estilos (copie do molde)
- Hub e faixas são contêineres de verdade, mas **não** `swimlane`: `rounded=1;container=1;collapsible=0;html=1;align=left;verticalAlign=top;spacingLeft=14;...`. O rótulo fica no canto, sem faixa de título. Os filhos usam `parent` e coordenadas relativas, como em `layout.md`.
- Pílula (filtro, rota): `rounded=1;arcSize=50;html=1;`, altura 30.
- Caixa por rota dentro de uma faixa: `rounded=1;arcSize=20;`, altura 30, borda `#a5b4fc`.
- Texto livre (nota de uma faixa, calha, detalhe do hub): `text;html=1;align=left;verticalAlign=middle;`.
- Seta: `edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;endSize=5;strokeColor=#64748b;strokeWidth=1.5;`. Na seta entre duas pílulas de destaque, use `strokeColor=#4f46e5`.
- **Fronteira** (a origem entra no hub; o hub fala com um destino): acrescente `startArrow=block;startFill=1;startSize=5;`, porque a resposta volta pelo mesmo caminho. Dentro do hub, a seta tem uma ponta só.

## Texto
- Rótulos em HTML (`html=1`), com hierarquia: título `<b>` e subtítulo em `<span style="color:#64748b">`, na mesma linha ou na de baixo.
- **Identificadores de código** (rotas, filtros, hosts, portas, chaves) em monoespaçado: `<span style="font-family:Menlo,Consolas,monospace">`. Não use `fontFamily=Menlo` no estilo: sem a fonte instalada, o draw.io cai para serifa.
- Aqui o detalhe que o leitor precisa (host:porta, endpoint) fica **visível**, em até 3 linhas monoespaçadas de 11 px. O resto vai para o `tooltip`, como nos outros tipos.
- Rótulo de seta só na fronteira (protocolo: `HTTPS`, `HTTP`, `gRPC`), deslocado para o lado com `<mxPoint x="25" y="0" as="offset"/>`. Setas internas não levam rótulo: a faixa de destino já diz o que acontece.

## Tamanhos
- Hub: 940 de largura (3 colunas). Faixa de uma linha: 50 de altura; de duas linhas: 90; de infraestrutura: 40. 20 px entre faixas e, entre a faixa e a linha de pílulas, 30 px.
- Pílula: 30 de altura; largura `max(120, 8 × caracteres)` arredondada para 10. Caixa de destino: 200 × 90.
- Tudo em múltiplos de 10. Página de ~980 × 620 para 3 colunas.

## Fidelidade
- Cada faixa, rota e destino vem do fluxo escolhido ou de **Componentes**, com a ordem das etapas do fluxo. Item `[inferido]` leva `?` no rótulo.
- Rota sem destino conhecido não ganha coluna: vai para a pílula tracejada, ou para **Lacunas e dúvidas**.
- Mais de 5 colunas não cabe: agrupe os destinos parecidos em uma coluna (`3 serviços de leitura`) e liste-os no `tooltip`.

## Antes de entregar
- [ ] Cada backend numa coluna; tudo dele com o centro nela; só o barramento de fan-out é compartilhado.
- [ ] Portas explícitas (`exitX`/`entryX`) em toda seta que toca uma faixa larga.
- [ ] Um único destaque de cor, só nas etapas que são o assunto.
- [ ] Identificadores de código em monoespaçado via `<span>`.
- [ ] Setas de duas pontas só nas fronteiras.
- [ ] Validador e `route_check.py` em `OK`; PNG renderizado e olhado (SKILL.md, seção de validação).
