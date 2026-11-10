package store

import (
	"context"
	"errors"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/model"
)

var (
	ErrNotFound = errors.New("not found")
	ErrConflict = errors.New("already exists")
)

type Store interface {
	CreateTenant(ctx context.Context, slug, name string) (model.Tenant, error)
	ListTenants(ctx context.Context) ([]model.Tenant, error)
	GetTenantBySlug(ctx context.Context, slug string) (model.Tenant, error)
	CreateService(ctx context.Context, tenantID, name, protocol, realHost string, realPort int, realBasePath string) (model.Service, error)
	SetActiveUpstream(ctx context.Context, tenantID, serviceID, upstream string) error
	ListServiceViews(ctx context.Context) ([]model.ServiceView, error)
	ListServiceViewsByTenant(ctx context.Context, tenantID string) ([]model.ServiceView, error)
	Close() error
}
