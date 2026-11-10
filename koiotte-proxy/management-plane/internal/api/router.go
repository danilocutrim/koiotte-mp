package api

import (
	"context"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/store"
)

type Rebuilder interface {
	Rebuild(ctx context.Context) error
}

type server struct {
	store store.Store
	mgr   Rebuilder
}

func New(st store.Store, mgr Rebuilder) http.Handler {
	s := &server{store: st, mgr: mgr}
	r := chi.NewRouter()
	r.Get("/health", s.health)
	r.Route("/api", func(r chi.Router) {
		r.Post("/tenants", s.createTenant)
		r.Get("/tenants", s.listTenants)
		r.Get("/tenants/{slug}", s.getTenant)
		r.Post("/tenants/{slug}/services", s.createService)
		r.Post("/tenants/{slug}/swap", s.swap)
		r.Get("/tenants/{slug}/status", s.tenantStatus)
		r.Get("/status", s.globalStatus)
	})
	return r
}
