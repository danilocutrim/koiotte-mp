package xds

import (
	"context"

	clusterservice "github.com/envoyproxy/go-control-plane/envoy/service/cluster/v3"
	discoverygrpc "github.com/envoyproxy/go-control-plane/envoy/service/discovery/v3"
	routeservice "github.com/envoyproxy/go-control-plane/envoy/service/route/v3"
	cachev3 "github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	serverv3 "github.com/envoyproxy/go-control-plane/pkg/server/v3"
	"google.golang.org/grpc"
)

func NewADSServer(cache cachev3.SnapshotCache) *grpc.Server {
	srv := serverv3.NewServer(context.Background(), cache, nil)
	gs := grpc.NewServer()
	discoverygrpc.RegisterAggregatedDiscoveryServiceServer(gs, srv)
	clusterservice.RegisterClusterDiscoveryServiceServer(gs, srv)
	routeservice.RegisterRouteDiscoveryServiceServer(gs, srv)
	return gs
}
