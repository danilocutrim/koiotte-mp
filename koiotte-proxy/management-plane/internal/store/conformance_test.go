package store

import (
	"context"
	"errors"
	"testing"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/model"
	"github.com/stretchr/testify/require"
)

func RunStoreConformance(t *testing.T, newStore func() Store) {
	ctx := context.Background()

	t.Run("create and get tenant", func(t *testing.T) {
		s := newStore()
		defer s.Close()
		tn, err := s.CreateTenant(ctx, "clienteA", "Cliente A")
		require.NoError(t, err)
		require.NotEmpty(t, tn.ID)
		got, err := s.GetTenantBySlug(ctx, "clienteA")
		require.NoError(t, err)
		require.Equal(t, tn.ID, got.ID)
	})

	t.Run("duplicate slug conflicts", func(t *testing.T) {
		s := newStore()
		defer s.Close()
		_, err := s.CreateTenant(ctx, "dup", "x")
		require.NoError(t, err)
		_, err = s.CreateTenant(ctx, "dup", "y")
		require.ErrorIs(t, err, ErrConflict)
	})

	t.Run("missing tenant is ErrNotFound", func(t *testing.T) {
		s := newStore()
		defer s.Close()
		_, err := s.GetTenantBySlug(ctx, "ghost")
		require.ErrorIs(t, err, ErrNotFound)
	})

	t.Run("service defaults to real and appears in views", func(t *testing.T) {
		s := newStore()
		defer s.Close()
		tn, _ := s.CreateTenant(ctx, "clienteA", "A")
		svc, err := s.CreateService(ctx, tn.ID, "pagamentos", "http", "backend-a", 8080, "/")
		require.NoError(t, err)
		views, err := s.ListServiceViews(ctx)
		require.NoError(t, err)
		require.Len(t, views, 1)
		require.Equal(t, "clienteA", views[0].TenantSlug)
		require.Equal(t, "pagamentos", views[0].Service.Name)
		require.Equal(t, model.UpstreamReal, views[0].ActiveUpstream)
		require.Equal(t, svc.ID, views[0].Service.ID)
	})

	t.Run("swap updates active upstream in isolation", func(t *testing.T) {
		s := newStore()
		defer s.Close()
		a, _ := s.CreateTenant(ctx, "clienteA", "A")
		b, _ := s.CreateTenant(ctx, "clienteB", "B")
		sa, _ := s.CreateService(ctx, a.ID, "pagamentos", "http", "ba", 8080, "/")
		_, _ = s.CreateService(ctx, b.ID, "pagamentos", "http", "bb", 8080, "/")

		require.NoError(t, s.SetActiveUpstream(ctx, a.ID, sa.ID, model.UpstreamVirtual))

		views, _ := s.ListServiceViewsByTenant(ctx, b.ID)
		require.Len(t, views, 1)
		require.Equal(t, model.UpstreamReal, views[0].ActiveUpstream, "clienteB must be unaffected by clienteA swap")
	})

	t.Run("swap to unknown service is ErrNotFound", func(t *testing.T) {
		s := newStore()
		defer s.Close()
		a, _ := s.CreateTenant(ctx, "clienteA", "A")
		err := s.SetActiveUpstream(ctx, a.ID, "nope", model.UpstreamVirtual)
		require.True(t, errors.Is(err, ErrNotFound))
	})
}
