package model

import "time"

const (
	UpstreamReal    = "real"
	UpstreamVirtual = "virtual"
)

type Tenant struct {
	ID        string
	Slug      string
	Name      string
	CreatedAt time.Time
}

type Service struct {
	ID           string
	TenantID     string
	Name         string
	Protocol     string
	RealHost     string
	RealPort     int
	RealBasePath string
	CreatedAt    time.Time
}

type RoutingState struct {
	TenantID       string
	ServiceID      string
	ActiveUpstream string
	Version        int64
}

type ServiceView struct {
	TenantSlug     string
	Service        Service
	ActiveUpstream string
}
