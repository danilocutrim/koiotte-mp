package store

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/model"
)

type SQLStore struct {
	db       *sql.DB
	ph       func(n int) string
	isUnique func(error) bool
}

const ddl = `
CREATE TABLE IF NOT EXISTS tenants (
	id TEXT PRIMARY KEY,
	slug TEXT NOT NULL UNIQUE,
	name TEXT NOT NULL,
	created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS services (
	id TEXT PRIMARY KEY,
	tenant_id TEXT NOT NULL REFERENCES tenants(id),
	name TEXT NOT NULL,
	protocol TEXT NOT NULL DEFAULT 'http',
	real_host TEXT NOT NULL,
	real_port INTEGER NOT NULL,
	real_base_path TEXT NOT NULL DEFAULT '/',
	created_at TEXT NOT NULL,
	UNIQUE(tenant_id, name)
);
CREATE TABLE IF NOT EXISTS routing_state (
	tenant_id TEXT NOT NULL,
	service_id TEXT NOT NULL,
	active_upstream TEXT NOT NULL DEFAULT 'real',
	version INTEGER NOT NULL DEFAULT 0,
	updated_at TEXT NOT NULL,
	PRIMARY KEY (tenant_id, service_id)
);`

func (s *SQLStore) migrate() error {
	for _, stmt := range strings.Split(ddl, ";") {
		if strings.TrimSpace(stmt) == "" {
			continue
		}
		if _, err := s.db.Exec(stmt); err != nil {
			return fmt.Errorf("migrate: %w", err)
		}
	}
	return nil
}

func newID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func now() string { return time.Now().UTC().Format(time.RFC3339Nano) }

func (s *SQLStore) CreateTenant(ctx context.Context, slug, name string) (model.Tenant, error) {
	t := model.Tenant{ID: newID(), Slug: slug, Name: name, CreatedAt: time.Now().UTC()}
	q := fmt.Sprintf("INSERT INTO tenants(id,slug,name,created_at) VALUES(%s,%s,%s,%s)",
		s.ph(1), s.ph(2), s.ph(3), s.ph(4))
	if _, err := s.db.ExecContext(ctx, q, t.ID, t.Slug, t.Name, now()); err != nil {
		if s.isUnique(err) {
			return model.Tenant{}, ErrConflict
		}
		return model.Tenant{}, err
	}
	return t, nil
}

func (s *SQLStore) ListTenants(ctx context.Context) ([]model.Tenant, error) {
	rows, err := s.db.QueryContext(ctx, "SELECT id,slug,name,created_at FROM tenants ORDER BY slug")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.Tenant
	for rows.Next() {
		var t model.Tenant
		var ts string
		if err := rows.Scan(&t.ID, &t.Slug, &t.Name, &ts); err != nil {
			return nil, err
		}
		t.CreatedAt, _ = time.Parse(time.RFC3339Nano, ts)
		out = append(out, t)
	}
	return out, rows.Err()
}

func (s *SQLStore) GetTenantBySlug(ctx context.Context, slug string) (model.Tenant, error) {
	q := fmt.Sprintf("SELECT id,slug,name,created_at FROM tenants WHERE slug=%s", s.ph(1))
	var t model.Tenant
	var ts string
	err := s.db.QueryRowContext(ctx, q, slug).Scan(&t.ID, &t.Slug, &t.Name, &ts)
	if errors.Is(err, sql.ErrNoRows) {
		return model.Tenant{}, ErrNotFound
	}
	if err != nil {
		return model.Tenant{}, err
	}
	t.CreatedAt, _ = time.Parse(time.RFC3339Nano, ts)
	return t, nil
}

func (s *SQLStore) CreateService(ctx context.Context, tenantID, name, protocol, realHost string, realPort int, realBasePath string) (model.Service, error) {
	if protocol == "" {
		protocol = "http"
	}
	if realBasePath == "" {
		realBasePath = "/"
	}
	svc := model.Service{
		ID: newID(), TenantID: tenantID, Name: name, Protocol: protocol,
		RealHost: realHost, RealPort: realPort, RealBasePath: realBasePath, CreatedAt: time.Now().UTC(),
	}
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return model.Service{}, err
	}
	defer tx.Rollback()

	q1 := fmt.Sprintf(`INSERT INTO services(id,tenant_id,name,protocol,real_host,real_port,real_base_path,created_at)
		VALUES(%s,%s,%s,%s,%s,%s,%s,%s)`,
		s.ph(1), s.ph(2), s.ph(3), s.ph(4), s.ph(5), s.ph(6), s.ph(7), s.ph(8))
	if _, err := tx.ExecContext(ctx, q1, svc.ID, svc.TenantID, svc.Name, svc.Protocol,
		svc.RealHost, svc.RealPort, svc.RealBasePath, now()); err != nil {
		if s.isUnique(err) {
			return model.Service{}, ErrConflict
		}
		return model.Service{}, err
	}
	q2 := fmt.Sprintf(`INSERT INTO routing_state(tenant_id,service_id,active_upstream,version,updated_at)
		VALUES(%s,%s,'real',0,%s)`, s.ph(1), s.ph(2), s.ph(3))
	if _, err := tx.ExecContext(ctx, q2, svc.TenantID, svc.ID, now()); err != nil {
		return model.Service{}, err
	}
	return svc, tx.Commit()
}

func (s *SQLStore) SetActiveUpstream(ctx context.Context, tenantID, serviceID, upstream string) error {
	q := fmt.Sprintf(`UPDATE routing_state SET active_upstream=%s, version=version+1, updated_at=%s
		WHERE tenant_id=%s AND service_id=%s`, s.ph(1), s.ph(2), s.ph(3), s.ph(4))
	res, err := s.db.ExecContext(ctx, q, upstream, now(), tenantID, serviceID)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

const viewSelect = `
SELECT t.slug, s.id, s.tenant_id, s.name, s.protocol, s.real_host, s.real_port, s.real_base_path, s.created_at, r.active_upstream
FROM services s
JOIN tenants t ON t.id = s.tenant_id
JOIN routing_state r ON r.service_id = s.id`

func (s *SQLStore) scanViews(rows *sql.Rows) ([]model.ServiceView, error) {
	defer rows.Close()
	var out []model.ServiceView
	for rows.Next() {
		var v model.ServiceView
		var ts string
		if err := rows.Scan(&v.TenantSlug, &v.Service.ID, &v.Service.TenantID, &v.Service.Name,
			&v.Service.Protocol, &v.Service.RealHost, &v.Service.RealPort, &v.Service.RealBasePath,
			&ts, &v.ActiveUpstream); err != nil {
			return nil, err
		}
		v.Service.CreatedAt, _ = time.Parse(time.RFC3339Nano, ts)
		out = append(out, v)
	}
	return out, rows.Err()
}

func (s *SQLStore) ListServiceViews(ctx context.Context) ([]model.ServiceView, error) {
	rows, err := s.db.QueryContext(ctx, viewSelect+" ORDER BY t.slug, s.name")
	if err != nil {
		return nil, err
	}
	return s.scanViews(rows)
}

func (s *SQLStore) ListServiceViewsByTenant(ctx context.Context, tenantID string) ([]model.ServiceView, error) {
	q := viewSelect + fmt.Sprintf(" WHERE s.tenant_id=%s ORDER BY s.name", s.ph(1))
	rows, err := s.db.QueryContext(ctx, q, tenantID)
	if err != nil {
		return nil, err
	}
	return s.scanViews(rows)
}

func (s *SQLStore) Close() error { return s.db.Close() }
