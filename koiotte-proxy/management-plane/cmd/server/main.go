package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/koiotte/koiotte-proxy/management-plane/internal/api"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/config"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/snapshot"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/store"
	"github.com/koiotte/koiotte-proxy/management-plane/internal/xds"
)

func main() {
	if len(os.Args) > 1 && os.Args[1] == "validate" {
		path := "/etc/koiotte/koiotte.yaml"
		if len(os.Args) > 2 {
			path = os.Args[2]
		}
		if errs := config.Validate(path); len(errs) > 0 {
			for _, e := range errs {
				fmt.Fprintln(os.Stderr, "ERRO:", e)
			}
			os.Exit(1)
		}
		fmt.Println("koiotte.yaml válido:", path)
		return
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config: %v", err)
	}

	var st store.Store
	switch cfg.Driver {
	case "postgres":
		st, err = store.OpenPostgres(cfg.DSN)
	default:
		st, err = store.OpenSQLite(cfg.DSN)
	}
	if err != nil {
		log.Fatalf("store: %v", err)
	}
	defer st.Close()

	mgr := xds.NewManager(st, snapshot.Engine{Host: cfg.EngineHost, Port: cfg.EnginePort})
	if err := mgr.Rebuild(context.Background()); err != nil {
		log.Fatalf("initial rebuild: %v", err)
	}

	lis, err := net.Listen("tcp", cfg.XDSAddr)
	if err != nil {
		log.Fatalf("xds listen: %v", err)
	}
	gs := xds.NewADSServer(mgr.Cache())
	go func() {
		log.Printf("xDS ADS server on %s", cfg.XDSAddr)
		if err := gs.Serve(lis); err != nil {
			log.Printf("xds serve stopped: %v", err)
		}
	}()

	srv := &http.Server{Addr: cfg.APIAddr, Handler: api.New(st, mgr)}
	go func() {
		log.Printf("Control API on %s", cfg.APIAddr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("http serve: %v", err)
		}
	}()

	<-ctx.Done()
	log.Printf("shutdown signal received, draining...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("http shutdown: %v", err)
	}
	if !stopGracefully(shutdownCtx, gs) {
		log.Printf("xds graceful stop timed out, forcing stop")
	}
	log.Printf("shutdown complete")
}

type grpcStopper interface {
	GracefulStop()
	Stop()
}

// GracefulStop waits for every open stream, and Envoy's ADS stream never ends on its own: without
// the deadline the process hangs after SIGTERM with the Control API already closed.
func stopGracefully(ctx context.Context, s grpcStopper) bool {
	done := make(chan struct{})
	go func() {
		s.GracefulStop()
		close(done)
	}()
	select {
	case <-done:
		return true
	case <-ctx.Done():
		s.Stop()
		<-done
		return false
	}
}
