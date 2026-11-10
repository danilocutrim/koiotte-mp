package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strconv"

	"github.com/go-chi/chi/v5"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/model"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/store"
)

type svcInput struct {
	Name         string `json:"name"`
	RealURL      string `json:"real_url"`
	RealHost     string `json:"real_host"`
	RealPort     int    `json:"real_port"`
	RealBasePath string `json:"real_base_path"`
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeJSON(w, http.StatusNotFound, map[string]string{"error": err.Error()})
	case errors.Is(err, store.ErrConflict):
		writeJSON(w, http.StatusConflict, map[string]string{"error": err.Error()})
	default:
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
}

func parseRealTarget(in svcInput) (scheme, host string, port int, basePath string, err error) {
	if in.RealURL != "" {
		u, perr := url.Parse(in.RealURL)
		if perr != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") {
			return "", "", 0, "", fmt.Errorf("invalid real_url")
		}
		scheme = u.Scheme
		host = u.Hostname()
		if p := u.Port(); p != "" {
			port, _ = strconv.Atoi(p)
		} else if scheme == "https" {
			port = 443
		} else {
			port = 80
		}
		basePath = u.Path
		if basePath == "" {
			basePath = "/"
		}
		return scheme, host, port, basePath, nil
	}
	scheme, host, port, basePath = "http", in.RealHost, in.RealPort, in.RealBasePath
	if basePath == "" {
		basePath = "/"
	}
	return scheme, host, port, basePath, nil
}

func (s *server) addService(w http.ResponseWriter, r *http.Request, tenantID string, in svcInput) (model.Service, bool) {
	scheme, host, port, basePath, err := parseRealTarget(in)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return model.Service{}, false
	}
	svc, err := s.store.CreateService(r.Context(), tenantID, in.Name, scheme, host, port, basePath)
	if err != nil {
		writeErr(w, err)
		return model.Service{}, false
	}
	return svc, true
}

func (s *server) health(w http.ResponseWriter, r *http.Request) {
	if _, err := s.store.ListTenants(r.Context()); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable", "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) createTenant(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Slug     string     `json:"slug"`
		Name     string     `json:"name"`
		Services []svcInput `json:"services"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Slug == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "slug required"})
		return
	}
	tn, err := s.store.CreateTenant(r.Context(), body.Slug, body.Name)
	if err != nil {
		writeErr(w, err)
		return
	}
	tenantCreated := true

	for _, in := range body.Services {
		if _, ok := s.addService(w, r, tn.ID, in); !ok {
			if tenantCreated {
				_ = s.mgr.Rebuild(r.Context())
			}
			return
		}
	}
	if err := s.mgr.Rebuild(r.Context()); err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, map[string]string{"slug": tn.Slug, "name": tn.Name})
}

func (s *server) listTenants(w http.ResponseWriter, r *http.Request) {
	tns, err := s.store.ListTenants(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	out := make([]map[string]string, 0, len(tns))
	for _, t := range tns {
		out = append(out, map[string]string{"slug": t.Slug, "name": t.Name})
	}
	writeJSON(w, http.StatusOK, out)
}

func (s *server) getTenant(w http.ResponseWriter, r *http.Request) {
	tn, err := s.store.GetTenantBySlug(r.Context(), chi.URLParam(r, "slug"))
	if err != nil {
		writeErr(w, err)
		return
	}
	views, err := s.store.ListServiceViewsByTenant(r.Context(), tn.ID)
	if err != nil {
		writeErr(w, err)
		return
	}
	svcs := make([]map[string]any, 0, len(views))
	for _, v := range views {
		svcs = append(svcs, map[string]any{
			"name": v.Service.Name, "active_upstream": v.ActiveUpstream,
			"real_host": v.Service.RealHost, "real_port": v.Service.RealPort,
			"real_base_path": v.Service.RealBasePath,
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"slug": tn.Slug, "name": tn.Name, "services": svcs})
}

func (s *server) createService(w http.ResponseWriter, r *http.Request) {
	tn, err := s.store.GetTenantBySlug(r.Context(), chi.URLParam(r, "slug"))
	if err != nil {
		writeErr(w, err)
		return
	}
	var in svcInput
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil || in.Name == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "name required"})
		return
	}
	svc, ok := s.addService(w, r, tn.ID, in)
	if !ok {
		return
	}
	if err := s.mgr.Rebuild(r.Context()); err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, map[string]string{"name": svc.Name})
}

func (s *server) swap(w http.ResponseWriter, r *http.Request) {
	tn, err := s.store.GetTenantBySlug(r.Context(), chi.URLParam(r, "slug"))
	if err != nil {
		writeErr(w, err)
		return
	}
	var body struct {
		Service string `json:"service"`
		To      string `json:"to"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "bad body"})
		return
	}
	if body.To != model.UpstreamReal && body.To != model.UpstreamVirtual {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "to must be real|virtual"})
		return
	}
	views, err := s.store.ListServiceViewsByTenant(r.Context(), tn.ID)
	if err != nil {
		writeErr(w, err)
		return
	}
	var serviceID string
	for _, v := range views {
		if v.Service.Name == body.Service {
			serviceID = v.Service.ID
			break
		}
	}
	if serviceID == "" {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "service not found"})
		return
	}
	if err := s.store.SetActiveUpstream(r.Context(), tn.ID, serviceID, body.To); err != nil {
		writeErr(w, err)
		return
	}
	if err := s.mgr.Rebuild(r.Context()); err != nil {
		writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"service": body.Service, "active_upstream": body.To})
}

func (s *server) tenantStatus(w http.ResponseWriter, r *http.Request) {
	tn, err := s.store.GetTenantBySlug(r.Context(), chi.URLParam(r, "slug"))
	if err != nil {
		writeErr(w, err)
		return
	}
	views, err := s.store.ListServiceViewsByTenant(r.Context(), tn.ID)
	if err != nil {
		writeErr(w, err)
		return
	}
	svcs := make([]map[string]string, 0, len(views))
	for _, v := range views {
		svcs = append(svcs, map[string]string{"name": v.Service.Name, "active_upstream": v.ActiveUpstream})
	}
	writeJSON(w, http.StatusOK, map[string]any{"slug": tn.Slug, "services": svcs})
}

func (s *server) globalStatus(w http.ResponseWriter, r *http.Request) {
	views, err := s.store.ListServiceViews(r.Context())
	if err != nil {
		writeErr(w, err)
		return
	}
	out := make([]map[string]string, 0, len(views))
	for _, v := range views {
		out = append(out, map[string]string{
			"tenant": v.TenantSlug, "service": v.Service.Name, "active_upstream": v.ActiveUpstream,
		})
	}
	writeJSON(w, http.StatusOK, out)
}
