package xds

import (
	"context"
	"strconv"
	"sync"
	"testing"

	resourcev3 "github.com/envoyproxy/go-control-plane/pkg/resource/v3"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/snapshot"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/store"
	"github.com/stretchr/testify/require"
)

func newStore(t *testing.T) store.Store {
	s, err := store.OpenSQLite("file::memory:?cache=shared&_pragma=busy_timeout(5000)")
	require.NoError(t, err)
	return s
}

func TestRebuildPublishesSnapshot(t *testing.T) {
	ctx := context.Background()
	st := newStore(t)
	defer st.Close()
	tn, _ := st.CreateTenant(ctx, "clienteA", "A")
	_, _ = st.CreateService(ctx, tn.ID, "pagamentos", "http", "backend-a", 8080, "/")

	m := NewManager(st, snapshot.Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, m.Rebuild(ctx))

	snap, err := m.Cache().GetSnapshot(NodeID)
	require.NoError(t, err)
	cds := snap.GetResources(resourcev3.ClusterType)
	require.Contains(t, cds, "clienteA_pagamentos_real")
	require.Contains(t, cds, snapshot.EngineClusterName)
}

func TestRebuildBumpsVersion(t *testing.T) {
	ctx := context.Background()
	st := newStore(t)
	defer st.Close()
	m := NewManager(st, snapshot.Engine{Host: "e", Port: 8081})
	require.NoError(t, m.Rebuild(ctx))
	v1, _ := m.Cache().GetSnapshot(NodeID)
	require.NoError(t, m.Rebuild(ctx))
	v2, _ := m.Cache().GetSnapshot(NodeID)
	require.NotEqual(t, v1.GetVersion(resourcev3.ClusterType), v2.GetVersion(resourcev3.ClusterType))
}

func TestRebuildConcurrentSerializes(t *testing.T) {
	ctx := context.Background()
	st := newStore(t)
	defer st.Close()
	m := NewManager(st, snapshot.Engine{Host: "e", Port: 8081})

	const n = 50
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			require.NoError(t, m.Rebuild(ctx))
		}()
	}
	wg.Wait()

	snap, err := m.Cache().GetSnapshot(NodeID)
	require.NoError(t, err)
	require.Equal(t, strconv.Itoa(n), snap.GetVersion(resourcev3.ClusterType))
}
