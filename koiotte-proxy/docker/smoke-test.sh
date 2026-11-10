#!/usr/bin/env bash
set -euo pipefail

MP=http://localhost:8080
PROXY=http://localhost:10000
MANAGER=http://localhost:8888

echo "== 1. create tenant clienteA with service pagamentos (real -> httpbin echo) =="
curl -fsS -X POST "$MP/api/tenants" -H 'content-type: application/json' -d '{
  "slug":"clienteA","name":"Cliente A",
  "services":[{"name":"pagamentos","real_url":"http://httpbin/anything/"}]
}'

echo; echo "== 2. proxy -> REAL should reach the echo backend =="
echo "  waiting for Envoy to pull the ADS config for clienteA (RDS/CDS propagation)..."
REAL_OK=0
for i in $(seq 1 30); do
  if curl -fsS "$PROXY/clienteA/pagamentos/abc-123" 2>/dev/null | grep -q '"url".*"http://[^"]*/anything/abc-123"'; then
    REAL_OK=1
    break
  fi
  sleep 0.5
done
if [ "$REAL_OK" -eq 1 ]; then
  echo "REAL ok (path stripped to /anything/abc-123, after $i attempt(s))"
else
  echo "REAL FAILED: proxy did not route to httpbin after 30 attempts" >&2
  echo "-- last response --" >&2
  curl -fsS "$PROXY/clienteA/pagamentos/abc-123" 2>&1 || true
  exit 1
fi

echo "== 3. create the matching virtual stub in Koiotte (workspace=clienteA, api=pagamentos) =="
WS=$(curl -fsS -X POST "$MANAGER/workspaces" -H 'content-type: application/json' \
  -d '{"name":"clienteA"}' | jq -r .id)
API=$(curl -fsS -X POST "$MANAGER/workspaces/$WS/apis" -H 'content-type: application/json' \
  -d '{"name":"pagamentos"}' | jq -r .id)
RES=$(curl -fsS -X POST "$MANAGER/workspaces/$WS/apis/$API/resources" -H 'content-type: application/json' \
  -d '{"name":"pay","path":"/abc-123","description":"smoke"}' | jq -r .id)
METHOD=$(curl -fsS -X POST "$MANAGER/workspaces/$WS/apis/$API/resources/$RES/methods" -H 'content-type: application/json' \
  -d '{"type":"GET","description":"smoke"}' | jq -r .id)
curl -fsS -X POST "$MANAGER/workspaces/$WS/apis/$API/resources/$RES/methods/$METHOD/stubs" \
  -H 'content-type: application/json' -d '{
    "workspace":"clienteA","name":"pay-virtual","apiName":"pagamentos",
    "incoming":{"protocol":"http","request":{"path":"/abc-123","method":"GET","name":"pagamentos","pathVariables":[],"queryParams":{},"headers":{},"body":null}},
    "outgoing":{"protocol":"http","response":{"code":200,"name":"pagamentos","headers":{"Content-Type":"application/json"},"body":"{\"virtual\":true}"}}
  }' > /dev/null
echo "  created workspace=$WS api=$API resource=$RES method=$METHOD stub for /abc-123 returning {\"virtual\":true}"

echo "  waiting for Engine to index/sync the stub (event-driven, ~20ms, poll defensively)..."
for i in $(seq 1 30); do
  if curl -fsS "http://localhost:8081/clienteA/pagamentos/abc-123" 2>/dev/null | grep -q '"virtual":true'; then
    echo "  Engine serving stub directly ok (after $i attempt(s))"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Engine never indexed the virtual stub after 30 attempts" >&2
    exit 1
  fi
  sleep 0.5
done

echo "== 4. swap clienteA/pagamentos -> virtual =="
curl -fsS -X POST "$MP/api/tenants/clienteA/swap" -H 'content-type: application/json' \
  -d '{"service":"pagamentos","to":"virtual"}'

echo; echo "== 5. same proxy call must now be served by the Engine (virtual stub) =="
VIRTUAL_OK=0
for i in $(seq 1 20); do
  if curl -fsS "$PROXY/clienteA/pagamentos/abc-123" 2>/dev/null | grep -q '"virtual":true'; then
    VIRTUAL_OK=1
    break
  fi
  sleep 0.5
done
if [ "$VIRTUAL_OK" -eq 1 ]; then
  echo "VIRTUAL ok (served by Koiotte Engine)"
else
  echo "VIRTUAL FAILED: proxy did not route to Engine after swap" >&2
  echo "-- last response body --" >&2
  curl -fsS "$PROXY/clienteA/pagamentos/abc-123" 2>&1 || true
  exit 1
fi

echo "== 6. isolation: create clienteB, confirm its route is untouched by A's swap =="
curl -fsS -X POST "$MP/api/tenants" -H 'content-type: application/json' -d '{
  "slug":"clienteB","name":"Cliente B",
  "services":[{"name":"pagamentos","real_url":"http://httpbin/anything/"}]
}'
if curl -fsS "$MP/api/tenants/clienteB/status" | grep -q '"active_upstream":"real"'; then
  echo "ISOLATION ok (clienteB still real)"
else
  echo "ISOLATION FAILED: clienteB is not real" >&2
  echo "-- last response --" >&2
  curl -fsS "$MP/api/tenants/clienteB/status" 2>&1 || true
  exit 1
fi

echo "== 7. global status =="
curl -fsS "$MP/api/status"
echo

echo "== 8. https real: TLS + host_rewrite na config do Envoy =="
curl -fsS -X POST "$MP/api/tenants" -H 'content-type: application/json' -d '{
  "slug":"clienteHttps","name":"C-HTTPS",
  "services":[{"name":"api","real_url":"https://api.real.com/v1/"}]
}' >/dev/null
curl -fsS -X POST "$MP/api/tenants/clienteHttps/swap" -H 'content-type: application/json' \
  -d '{"service":"api","to":"real"}' >/dev/null

HTTPS_OK=0
for i in $(seq 1 20); do
  DUMP=$(docker exec koiotte-proxy-envoy bash -c '
    exec 3<>/dev/tcp/127.0.0.1/9901
    printf "GET /config_dump HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3
    cat <&3
  ' 2>/dev/null)
  if echo "$DUMP" | grep -q 'clienteHttps_api_real' \
     && echo "$DUMP" | grep -q 'transport_sockets.tls' \
     && echo "$DUMP" | grep -q 'api.real.com'; then
    HTTPS_OK=1
    break
  fi
  sleep 0.5
done
if [ "$HTTPS_OK" -eq 1 ]; then
  echo "https config OK (cluster clienteHttps_api_real with TLS + host_rewrite to api.real.com, after $i attempt(s))"
else
  echo "HTTPS config assertion FAILED (cluster/TLS/host_rewrite not found in config_dump after 20 attempts)" >&2
  exit 1
fi

echo; echo "SMOKE TEST PASSED"
