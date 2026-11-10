# koiotte-proxy

Modo **proxy + swap real↔virtual** para o Koiotte, baseado em **Envoy + Management Plane (Go)**.

> **Restrição dura:** este componente **não altera nenhum código em `/app`**. Consome o
> Koiotte Manager (8888) e o Engine (8081) apenas via HTTP.

## O que faz (v1)

Coloca o Koiotte inline como proxy reverso multi-tenant **por path**
(`proxy.dominio/{tenant}/{service}/...`) e permite **swap manual em runtime** entre:

- **real** — passthrough para o backend real do cliente (com strip do prefixo do tenant);
- **virtual** — o **Koiotte Engine** servindo os stubs daquele tenant.

Mapeamento com o Koiotte: `tenant.slug == workspace` e `service.name == apiName`.

## Estrutura

```
management-plane/   código Go (Control API, store SQLite/Postgres, snapshot builder, xDS/ADS)
envoy/              bootstrap do Envoy (ADS -> management-plane)
docker/             docker-compose de dev (envoy + management-plane [SQLite] + httpbin) + smoke-test.sh
```

## Como rodar

```bash
# Sobe envoy (proxy :10000) + management-plane (:8080 API, :18000 xDS) + httpbin (backend de teste)
docker compose -f koiotte-proxy/docker/docker-compose.yml up -d --build

# Testes unitários (Go 1.25; store SQLite roda sempre, Postgres exige KP_TEST_PG_DSN)
cd koiotte-proxy/management-plane && go test ./...

# Smoke test e2e (real -> virtual swap + isolamento entre tenants)
bash koiotte-proxy/docker/smoke-test.sh
```

### Portas

| Porta | Componente |
|---|---|
| 10000 | Envoy — listener do proxy multi-tenant |
| 8080  | Management Plane — Control API (`KP_API_ADDR`) |
| 18000 | Management Plane — xDS/ADS gRPC (`KP_XDS_ADDR`) |

### Control API

Todas as rotas sob `/api`:

| Método/rota | Função |
|---|---|
| `POST /api/tenants` | cria tenant |
| `GET /api/tenants` | lista tenants |
| `GET /api/tenants/{slug}` | detalha tenant |
| `POST /api/tenants/{slug}/services` | registra service (backend real) |
| `POST /api/tenants/{slug}/swap` | swap real↔virtual |
| `GET /api/tenants/{slug}/status` | estado de roteamento do tenant |
| `GET /api/status` | estado geral |

### Configuração (env vars)

| Var | Default | Descrição |
|---|---|---|
| `KP_DRIVER` | `sqlite` | driver do store (`sqlite` ou `postgres`) |
| `KP_DSN` | — | DSN do banco |
| `KP_API_ADDR` | `:8080` | endereço da Control API |
| `KP_XDS_ADDR` | `:18000` | endereço do servidor xDS/ADS |
| `KP_ENGINE_HOST` | `koiotte-app` | host do Koiotte Engine (modo virtual) |
| `KP_ENGINE_PORT` | `8081` | porta do Engine |

## Documentação

- Design v1: removido do repo em `9b41a183` (feature entregue); histórico no git
- Plano de implementação v1 (concluído): removido do repo em `a199cdae`; histórico no git

## Status

**v1 implementado (2026-07-17):** store SQLite/Postgres com suíte de conformidade compartilhada,
snapshot builder, xDS manager + ADS gRPC, Control API, wiring + bootstrap Envoy + compose,
smoke test e2e com gate de isolamento.

Roadmap pós-v1 (gravador, rollback/swap_history, auth, health-check/auto-swap, swap gradual,
gRPC/TCP, observabilidade, deploy Terraform, custom domain) descrito no design.
