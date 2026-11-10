package snapshot

import (
	"testing"

	clusterv3 "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	routev3 "github.com/envoyproxy/go-control-plane/envoy/config/route/v3"
	cachev3 "github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	resourcev3 "github.com/envoyproxy/go-control-plane/pkg/resource/v3"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/model"
	"github.com/stretchr/testify/require"
)

type cacheSnapshotAlias = cachev3.Snapshot

func views() []model.ServiceView {
	return []model.ServiceView{
		{TenantSlug: "clienteA", ActiveUpstream: model.UpstreamReal,
			Service: model.Service{Name: "pagamentos", RealHost: "backend-a", RealPort: 8080, RealBasePath: "/"}},
		{TenantSlug: "clienteB", ActiveUpstream: model.UpstreamVirtual,
			Service: model.Service{Name: "pagamentos", RealHost: "backend-b", RealPort: 8080, RealBasePath: "/pag"}},
	}
}

func routeConfig(t *testing.T, snap *cacheSnapshotAlias) *routev3.RouteConfiguration {
	res := snap.GetResources(resourcev3.RouteType)
	require.Len(t, res, 1)
	rc, ok := res[RouteConfigName].(*routev3.RouteConfiguration)
	require.True(t, ok)
	return rc
}

func TestRealClusterName(t *testing.T) {
	require.Equal(t, "clienteA_pagamentos_real", RealClusterName("clienteA", "pagamentos"))
}

func TestBuildHasClusters(t *testing.T) {
	snap, err := Build("1", views(), Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, err)
	cds := snap.GetResources(resourcev3.ClusterType)
	require.Len(t, cds, 3)
	require.Contains(t, cds, "clienteA_pagamentos_real")
	require.Contains(t, cds, "clienteB_pagamentos_real")
	require.Contains(t, cds, EngineClusterName)
	_, ok := cds[EngineClusterName].(*clusterv3.Cluster)
	require.True(t, ok)
}

func TestBuildRealRouteStripsPrefix(t *testing.T) {
	snap, err := Build("1", views(), Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, err)
	rc := routeConfig(t, snap)
	r := findRoute(t, rc, "/clienteA/pagamentos/")
	action := r.GetRoute()
	require.Equal(t, "clienteA_pagamentos_real", action.GetCluster())
	require.Equal(t, "/", action.GetPrefixRewrite())
}

func TestBuildVirtualRouteNoRewrite(t *testing.T) {
	snap, err := Build("1", views(), Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, err)
	rc := routeConfig(t, snap)
	r := findRoute(t, rc, "/clienteB/pagamentos/")
	action := r.GetRoute()
	require.Equal(t, EngineClusterName, action.GetCluster())
	require.Equal(t, "", action.GetPrefixRewrite(), "virtual must NOT rewrite the path")
}

func TestNormalizeBasePath(t *testing.T) {
	cases := map[string]string{
		"":       "/",
		"/":      "/",
		"/api":   "/api/",
		"/api/":  "/api/",
		"/api//": "/api/",
		"/v1/x":  "/v1/x/",
		"/v1/x/": "/v1/x/",
	}
	for in, want := range cases {
		require.Equal(t, want, normalizeBasePath(in), "normalizeBasePath(%q)", in)
	}
}

func TestBuildRealRouteRewriteHasTrailingSlash(t *testing.T) {
	views := []model.ServiceView{{
		TenantSlug:     "clienteA",
		Service:        model.Service{Name: "pagamentos", Protocol: "http", RealHost: "backend-a", RealPort: 8080, RealBasePath: "/api"},
		ActiveUpstream: model.UpstreamReal,
	}}
	snap, err := Build("1", views, Engine{Host: "e", Port: 8081})
	require.NoError(t, err)
	rc := routeConfig(t, snap)
	r := findRoute(t, rc, "/clienteA/pagamentos/")
	require.Equal(t, "/api/", r.GetRoute().GetPrefixRewrite())
}

func findRoute(t *testing.T, rc *routev3.RouteConfiguration, prefix string) *routev3.Route {
	require.Len(t, rc.VirtualHosts, 1)
	for _, r := range rc.VirtualHosts[0].Routes {
		if r.GetMatch().GetPrefix() == prefix {
			return r
		}
	}
	t.Fatalf("route with prefix %q not found", prefix)
	return nil
}

func TestBuildFallbackRouteToEngine(t *testing.T) {
	snap, err := Build("1", views(), Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, err)
	rc := routeConfig(t, snap)

	routes := rc.VirtualHosts[0].Routes
	last := routes[len(routes)-1]
	require.Equal(t, "/", last.GetMatch().GetPrefix())
	action := last.GetRoute()
	require.Equal(t, EngineClusterName, action.GetCluster())
	require.Equal(t, "", action.GetPrefixRewrite(), "fallback não pode reescrever o path")
}

func TestBuild_HttpsRealHasTLSAndHostRewrite(t *testing.T) {
	views := []model.ServiceView{{
		TenantSlug:     "clienteA",
		Service:        model.Service{Name: "pagamentos", Protocol: "https", RealHost: "api.real.com", RealPort: 443, RealBasePath: "/v1/"},
		ActiveUpstream: model.UpstreamReal,
	}}
	snap, err := Build("1", views, Engine{Host: "koiotte-engine", Port: 8081})
	require.NoError(t, err)

	cds := snap.GetResources(resourcev3.ClusterType)
	real := cds[RealClusterName("clienteA", "pagamentos")].(*clusterv3.Cluster)
	require.NotNil(t, real.TransportSocket, "https real cluster must have TLS transport socket")
	require.Equal(t, "envoy.transport_sockets.tls", real.TransportSocket.Name)

	rc := snap.GetResources(resourcev3.RouteType)[RouteConfigName].(*routev3.RouteConfiguration)
	realRoute := rc.VirtualHosts[0].Routes[0].GetRoute()
	require.Equal(t, "api.real.com", realRoute.GetHostRewriteLiteral())
	require.Equal(t, "/v1/", realRoute.GetPrefixRewrite())
}

func TestBuild_HttpRealHasNoTLS(t *testing.T) {
	views := []model.ServiceView{{
		TenantSlug:     "clienteB",
		Service:        model.Service{Name: "pag", Protocol: "http", RealHost: "httpbin", RealPort: 80, RealBasePath: "/"},
		ActiveUpstream: model.UpstreamReal,
	}}
	snap, err := Build("1", views, Engine{Host: "e", Port: 8081})
	require.NoError(t, err)
	real := snap.GetResources(resourcev3.ClusterType)[RealClusterName("clienteB", "pag")].(*clusterv3.Cluster)
	require.Nil(t, real.TransportSocket, "http real cluster must not have TLS")
}

func TestBuildSpecificRoutesPrecedeFallback(t *testing.T) {
	snap, err := Build("1", views(), Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, err)
	rc := routeConfig(t, snap)
	routes := rc.VirtualHosts[0].Routes
	require.Len(t, routes, 3)
	require.Equal(t, "/clienteA/pagamentos/", routes[0].GetMatch().GetPrefix())
	require.Equal(t, "/clienteB/pagamentos/", routes[1].GetMatch().GetPrefix())
	require.Equal(t, "/", routes[2].GetMatch().GetPrefix())
}

func TestBuild_ClustersPreferIPv4(t *testing.T) {
	snap, err := Build("1", views(), Engine{Host: "koiotte-app", Port: 8081})
	require.NoError(t, err)
	for name, res := range snap.GetResources(resourcev3.ClusterType) {
		c, ok := res.(*clusterv3.Cluster)
		require.True(t, ok)
		require.Equal(t, clusterv3.Cluster_V4_PREFERRED, c.GetDnsLookupFamily(), name)
	}
}
