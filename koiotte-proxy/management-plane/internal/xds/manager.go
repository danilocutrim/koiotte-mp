package xds

import (
	"context"
	"strconv"
	"sync"
	"sync/atomic"

	cachev3 "github.com/envoyproxy/go-control-plane/pkg/cache/v3"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/snapshot"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/store"
)

const NodeID = "koiotte-proxy"

type Manager struct {
	store   store.Store
	engine  snapshot.Engine
	cache   cachev3.SnapshotCache
	version atomic.Int64
	rebuildMu sync.Mutex
}

func NewManager(st store.Store, engine snapshot.Engine) *Manager {
	return &Manager{
		store:  st,
		engine: engine,
		cache:  cachev3.NewSnapshotCache(false, cachev3.IDHash{}, nil),
	}
}

func (m *Manager) Cache() cachev3.SnapshotCache { return m.cache }

func (m *Manager) Rebuild(ctx context.Context) error {
	m.rebuildMu.Lock()
	defer m.rebuildMu.Unlock()

	views, err := m.store.ListServiceViews(ctx)
	if err != nil {
		return err
	}
	version := strconv.FormatInt(m.version.Add(1), 10)
	snap, err := snapshot.Build(version, views, m.engine)
	if err != nil {
		return err
	}
	return m.cache.SetSnapshot(ctx, NodeID, snap)
}
