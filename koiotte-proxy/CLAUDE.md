# koiotte-proxy/ — Go

Proxy reverso multi-tenant que faz **swap real↔virtual em runtime, sem reiniciar nada**. Duas
peças:

- **Envoy** (`envoy/bootstrap.yaml`) — data plane. Recebe o tráfego em 10000, não conhece
  nenhuma rota estaticamente: tudo vem por ADS.
- **Management Plane** (`management-plane/`, Go 1.25) — control plane. Serve a Control API HTTP
  (8080) e o servidor xDS/ADS gRPC (18000).

O contrato entre eles é a rota `/{tenant}/{service}/...`. Trocar o upstream de um serviço é um
`POST /api/tenants/{slug}/swap` que reconstrói o snapshot xDS e o empurra para o Envoy.

## Comandos

```bash
cd koiotte-proxy/management-plane
go build ./... && go test ./...
go run ./cmd/server validate ../../dev-local/koiotte.yaml   # validador oficial do koiotte.yaml
go vet ./...
./docker/smoke-test.sh                                      # E2E do swap
```

O binário `server` é **gitignored**. Qualquer automação que precise do validador roda
`go run ./cmd/server validate`, nunca um binário pré-compilado.

## Control API

`internal/api/router.go` é a lista completa e curta — leia-a em vez de confiar em documentação:

```
GET  /health
POST /api/tenants                      GET /api/tenants        GET /api/tenants/{slug}
POST /api/tenants/{slug}/services
POST /api/tenants/{slug}/swap          GET /api/tenants/{slug}/status
GET  /api/status
```

`api.New(store, mgr)` recebe o manager pela interface `Rebuilder` (só `Rebuild(ctx)`) — a API
não conhece xDS. Mantenha assim: handler que fala protobuf de Envoy é acoplamento errado.

## Invariantes do snapshot (internal/snapshot/builder.go)

- **`normalizeBasePath` existe por um bug real de concatenação.** A rota casada
  (`/{tenant}/{service}/`) já traz a barra final, e o Envoy troca esse prefixo inteiro pelo
  `prefix_rewrite`. Sem normalizar, `real_base_path: "/api"` produzia `/apifoo`, e `"/api//"`
  duplicava. A função apara todas as barras finais e recoloca exatamente uma.
- Nomes de recurso são **derivados, não configurados** — os nomes de cluster e de route config
  saem de constantes em `internal/snapshot/builder.go`, e o cluster real segue
  `{tenant}_{service}_real`. Mudar um desses quebra o Envoy silenciosamente: a rota some e o
  tráfego cai em 404.
- O upstream ativo é um conjunto **fechado** de dois valores, "real" e "virtual". É string por
  causa do SQL, não por ser extensível.

## Store

Uma interface (`store.Store`), duas implementações, **um `sql.go` compartilhado** — sqlite.go e
postgres.go só abrem a conexão e delegam. Ao adicionar um método, ele vai em `sql.go`; se você
se pegar escrevendo SQL duas vezes, é sinal de que foi para o lugar errado.

`conformance_test.go` roda a mesma bateria contra os dois drivers — é o teste que impede
divergência de comportamento. Adicionou método? Adicione o caso lá.

Erros sentinela: `store.ErrNotFound` e `store.ErrConflict`. Os handlers mapeiam para 404/409 —
não invente erro novo para o mesmo caso.

SQLite é o default (`modernc.org/sqlite`, CGO-free — não quebre isso adicionando um driver que
exija CGO). DSN de dev traz `_pragma=busy_timeout(5000)`.

## Ciclo de vida

`main.go` faz `mgr.Rebuild()` **antes** de abrir os listeners — subir com snapshot vazio deixaria
o Envoy sem rota nenhuma numa janela observável. Shutdown é gracioso via `signal.NotifyContext`
+ `srv.Shutdown` com 10s e `gs.GracefulStop()` limitado ao mesmo prazo, depois `Stop()`: o stream
ADS do Envoy nunca termina sozinho, e sem o prazo o processo travava após o SIGTERM (o restart do
live_update do Tilt virava loop de liveness).

## Convenções Go

- Erros embrulhados com `%w`; comparação com `errors.Is`.
- Comentários: nenhum na árvore desde `c674613`. O modelo que esta linha citava era
  `normalizeBasePath` — `git show c674613^:koiotte-proxy/management-plane/internal/snapshot/builder.go`.
  Novos comentários, se houver, em inglês explicando o porquê (regra global — ver raiz).
- Testes com `testify`, tabelados quando há mais de dois casos.
- `internal/` é intencional: nada aqui é API pública.
- `migrations/` existe mas está vazio — o schema é criado pelo próprio `sql.go` hoje. Se
  introduzir migrations de verdade, atualize esta linha.