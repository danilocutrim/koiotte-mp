# Infra e deploy na AWS em draw.io

Fonte no `flow.md`: **Infra e deploy** (e **Componentes** para o que roda onde).

Leia antes `references/layout.md`: camadas, corredores e contêineres reais valem aqui também.

## Hierarquia de grupos (de fora para dentro)
Conta AWS → Região → VPC → Subnet (pública/privada) → recursos. Serviços gerenciados fora de VPC (S3, SQS, DynamoDB) ficam dentro da região, fora da VPC. Cada nível é um `swimlane` real, com os filhos parentados nele (coordenadas relativas). Só crie o nível de grupo que o `flow.md` ou os arquivos de infra (Terraform, CDK, CloudFormation) mostram.

**Serviços regionais ficam fora da VPC.** CloudWatch, CloudTrail e Config não vivem dentro de VPC nem de subnet: ponha-os numa zona de observabilidade na região, **fora da VPC**, com a seta de telemetria tracejada cruzando a borda. No máximo 2 setas de observabilidade no diagrama inteiro.

## Cores por categoria (retângulo com rótulo, estilo padrão da skill)
| Categoria | Cor | Exemplos |
|---|---|---|
| Compute | `#ED7100` | Lambda, ECS, EC2 |
| Storage | `#7AA116` | S3 |
| Database | `#C925D1` | DynamoDB, RDS |
| Networking | `#8C4FFF` | ALB, API Gateway, Route 53 |
| App integration | `#E7157B` | SQS, SNS, EventBridge |
| Security | `#DD344C` | IAM, KMS, Secrets Manager |

Estilo: `rounded=1;whiteSpace=wrap;html=1;fillColor=<COR>;fontColor=#ffffff;strokeColor=none;` e o rótulo `Nome (Serviço)`.

## Ícones oficiais (opcional)
Duas formas circulam para os ícones da biblioteca `mxgraph.aws4`: `shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<nome>;` e `shape=mxgraph.aws4.<nome>;`. Não há garantia de qual renderiza em cada versão. Use um ícone só se você tiver certeza do nome **e** conferir na renderização (PNG) que ele aparece. Um nome errado aparece em branco e o validador não pega. Na dúvida, use o retângulo colorido acima.

## Deploy
- Pipeline (CI/CD) vira uma faixa horizontal separada acima ou abaixo: `Repo → Build → Test → Deploy`, com seta para o ambiente.
- Ambientes (dev, stg, prod) viram grupos lado a lado com os mesmos recursos; não duplique detalhe: detalhe um e rotule os outros "igual a dev" se o código confirmar.
- Origem de cada recurso: cite `arquivo:linha` do IaC no `tooltip` do nó (atributo `tooltip` no `mxCell`) quando existir.
