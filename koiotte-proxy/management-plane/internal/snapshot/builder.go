package snapshot

import (
	"time"

	clusterv3 "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	corev3 "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	endpointv3 "github.com/envoyproxy/go-control-plane/envoy/config/endpoint/v3"
	routev3 "github.com/envoyproxy/go-control-plane/envoy/config/route/v3"
	tlsv3 "github.com/envoyproxy/go-control-plane/envoy/extensions/transport_sockets/tls/v3"
	"github.com/envoyproxy/go-control-plane/pkg/cache/types"
	cachev3 "github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	resourcev3 "github.com/envoyproxy/go-control-plane/pkg/resource/v3"
	"google.golang.org/protobuf/types/known/anypb"
	"google.golang.org/protobuf/types/known/durationpb"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/model"
)

const (
	EngineClusterName = "koiotte_engine"
	RouteConfigName   = "proxy_routes"
)

type Engine struct {
	Host string
	Port int
}

func RealClusterName(tenantSlug, serviceName string) string {
	return tenantSlug + "_" + serviceName + "_real"
}

func normalizeBasePath(p string) string {
	for len(p) > 0 && p[len(p)-1] == '/' {
		p = p[:len(p)-1]
	}
	return p + "/"
}

func strictDNSCluster(name, host string, port int) *clusterv3.Cluster {
	return &clusterv3.Cluster{
		Name:                 name,
		ConnectTimeout:       durationpb.New(time.Second),
		ClusterDiscoveryType: &clusterv3.Cluster_Type{Type: clusterv3.Cluster_STRICT_DNS},
		// Envoy's default (AUTO) prefers AAAA records; on IPv4-only networks (compose, microk8s pods)
		// a dual-stack host like www.google.com then fails with "Network is unreachable".
		DnsLookupFamily: clusterv3.Cluster_V4_PREFERRED,
		LbPolicy:        clusterv3.Cluster_ROUND_ROBIN,
		LoadAssignment: &endpointv3.ClusterLoadAssignment{
			ClusterName: name,
			Endpoints: []*endpointv3.LocalityLbEndpoints{{
				LbEndpoints: []*endpointv3.LbEndpoint{{
					HostIdentifier: &endpointv3.LbEndpoint_Endpoint{
						Endpoint: &endpointv3.Endpoint{
							Address: &corev3.Address{Address: &corev3.Address_SocketAddress{
								SocketAddress: &corev3.SocketAddress{
									Address:       host,
									PortSpecifier: &corev3.SocketAddress_PortValue{PortValue: uint32(port)},
								},
							}},
						},
					},
				}},
			}},
		},
	}
}

func Build(version string, views []model.ServiceView, engine Engine) (*cachev3.Snapshot, error) {
	clusters := []types.Resource{strictDNSCluster(EngineClusterName, engine.Host, engine.Port)}
	routes := make([]*routev3.Route, 0, len(views))

	for _, v := range views {
		realName := RealClusterName(v.TenantSlug, v.Service.Name)
		realCluster := strictDNSCluster(realName, v.Service.RealHost, v.Service.RealPort)
		if v.Service.Protocol == "https" {
			tlsCtx, terr := anypb.New(&tlsv3.UpstreamTlsContext{Sni: v.Service.RealHost})
			if terr != nil {
				return nil, terr
			}
			realCluster.TransportSocket = &corev3.TransportSocket{
				Name:       "envoy.transport_sockets.tls",
				ConfigType: &corev3.TransportSocket_TypedConfig{TypedConfig: tlsCtx},
			}
		}
		clusters = append(clusters, realCluster)

		prefix := "/" + v.TenantSlug + "/" + v.Service.Name + "/"
		action := &routev3.RouteAction{}
		if v.ActiveUpstream == model.UpstreamVirtual {
			action.ClusterSpecifier = &routev3.RouteAction_Cluster{Cluster: EngineClusterName}
		} else {
			action.ClusterSpecifier = &routev3.RouteAction_Cluster{Cluster: realName}
			action.PrefixRewrite = normalizeBasePath(v.Service.RealBasePath)
			action.HostRewriteSpecifier = &routev3.RouteAction_HostRewriteLiteral{HostRewriteLiteral: v.Service.RealHost}
		}
		routes = append(routes, &routev3.Route{
			Match:  &routev3.RouteMatch{PathSpecifier: &routev3.RouteMatch_Prefix{Prefix: prefix}},
			Action: &routev3.Route_Route{Route: action},
		})
	}

	routes = append(routes, &routev3.Route{
		Match: &routev3.RouteMatch{PathSpecifier: &routev3.RouteMatch_Prefix{Prefix: "/"}},
		Action: &routev3.Route_Route{Route: &routev3.RouteAction{
			ClusterSpecifier: &routev3.RouteAction_Cluster{Cluster: EngineClusterName},
		}},
	})

	routeConfig := &routev3.RouteConfiguration{
		Name: RouteConfigName,
		VirtualHosts: []*routev3.VirtualHost{{
			Name:    "proxy",
			Domains: []string{"*"},
			Routes:  routes,
		}},
	}

	return cachev3.NewSnapshot(version, map[resourcev3.Type][]types.Resource{
		resourcev3.ClusterType: clusters,
		resourcev3.RouteType:   {routeConfig},
	})
}
