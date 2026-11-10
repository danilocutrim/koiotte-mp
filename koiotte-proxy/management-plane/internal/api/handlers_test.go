package api

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/store"
	"github.com/stretchr/testify/require"
)

type fakeRebuilder struct{ calls int }

func (f *fakeRebuilder) Rebuild(context.Context) error { f.calls++; return nil }

func setup(t *testing.T) (http.Handler, *fakeRebuilder) {
	st, err := store.OpenSQLite("file::memory:?cache=shared&_pragma=busy_timeout(5000)")
	require.NoError(t, err)
	fr := &fakeRebuilder{}
	return New(st, fr), fr
}

func do(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	var buf bytes.Buffer
	if body != nil {
		require.NoError(t, json.NewEncoder(&buf).Encode(body))
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealthOK(t *testing.T) {
	h, _ := setup(t)
	rec := do(t, h, "GET", "/health", nil)
	require.Equal(t, http.StatusOK, rec.Code)
	var got map[string]string
	require.NoError(t, json.Unmarshal(rec.Body.Bytes(), &got))
	require.Equal(t, "ok", got["status"])
}

func TestCreateTenantTriggersRebuild(t *testing.T) {
	h, fr := setup(t)
	rec := do(t, h, "POST", "/api/tenants", map[string]any{
		"slug": "clienteA", "name": "A",
		"services": []map[string]any{{"name": "pagamentos", "real_host": "backend-a", "real_port": 8080}},
	})
	require.Equal(t, http.StatusCreated, rec.Code)
	require.GreaterOrEqual(t, fr.calls, 1)
}

func TestSwapChangesUpstreamAndRebuilds(t *testing.T) {
	h, fr := setup(t)
	do(t, h, "POST", "/api/tenants", map[string]any{
		"slug": "clienteA", "name": "A",
		"services": []map[string]any{{"name": "pagamentos", "real_host": "backend-a", "real_port": 8080}},
	})
	before := fr.calls
	rec := do(t, h, "POST", "/api/tenants/clienteA/swap", map[string]any{"service": "pagamentos", "to": "virtual"})
	require.Equal(t, http.StatusOK, rec.Code)
	require.Greater(t, fr.calls, before)

	rec = do(t, h, "GET", "/api/tenants/clienteA/status", nil)
	var got map[string]any
	require.NoError(t, json.Unmarshal(rec.Body.Bytes(), &got))
	svcs := got["services"].([]any)
	require.Equal(t, "virtual", svcs[0].(map[string]any)["active_upstream"])
}

func TestSwapInvalidTargetIs400(t *testing.T) {
	h, _ := setup(t)
	do(t, h, "POST", "/api/tenants", map[string]any{"slug": "clienteA", "name": "A"})
	rec := do(t, h, "POST", "/api/tenants/clienteA/swap", map[string]any{"service": "pagamentos", "to": "bogus"})
	require.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestSwapUnknownTenantIs404(t *testing.T) {
	h, _ := setup(t)
	rec := do(t, h, "POST", "/api/tenants/ghost/swap", map[string]any{"service": "x", "to": "real"})
	require.Equal(t, http.StatusNotFound, rec.Code)
}

func TestDuplicateTenantIs409(t *testing.T) {
	h, _ := setup(t)
	do(t, h, "POST", "/api/tenants", map[string]any{"slug": "dup", "name": "A"})
	rec := do(t, h, "POST", "/api/tenants", map[string]any{"slug": "dup", "name": "B"})
	require.Equal(t, http.StatusConflict, rec.Code)
}

func TestCreateTenantPartialServiceFailureStillRebuilds(t *testing.T) {
	h, fr := setup(t)
	rec := do(t, h, "POST", "/api/tenants", map[string]any{
		"slug": "partial", "name": "Partial Test",
		"services": []map[string]any{
			{"name": "svc1", "real_host": "host1", "real_port": 8080},
			{"name": "svc1", "real_host": "host2", "real_port": 8081},
		},
	})
	require.Equal(t, http.StatusConflict, rec.Code)

	require.GreaterOrEqual(t, fr.calls, 1)

	rec = do(t, h, "GET", "/api/tenants/partial", nil)
	require.Equal(t, http.StatusOK, rec.Code)
	var tenantResp map[string]any
	require.NoError(t, json.Unmarshal(rec.Body.Bytes(), &tenantResp))
	require.Equal(t, "partial", tenantResp["slug"])
	services := tenantResp["services"].([]any)
	require.Len(t, services, 1)
	require.Equal(t, "svc1", services[0].(map[string]any)["name"])
}
