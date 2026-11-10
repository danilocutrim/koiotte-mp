package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeYAML(t *testing.T, content string) string {
	t.Helper()
	p := filepath.Join(t.TempDir(), "koiotte.yaml")
	if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestLoadFromYAML(t *testing.T) {
	p := writeYAML(t, `
version: 1
proxy:
  management-plane:
    api-port: 9080
    xds-port: 19000
    engine-host: meu-engine
    engine-port: 9081
    database:
      driver: postgres
      dsn: "postgres://x"
`)
	t.Setenv("KOIOTTE_CONFIG", p)
	c, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if c.APIAddr != ":9080" || c.XDSAddr != ":19000" {
		t.Fatalf("addrs errados: %+v", c)
	}
	if c.EngineHost != "meu-engine" || c.EnginePort != 9081 {
		t.Fatalf("engine errado: %+v", c)
	}
	if c.Driver != "postgres" || c.DSN != "postgres://x" {
		t.Fatalf("db errado: %+v", c)
	}
}

func TestLoadDefaultsWhenNoFile(t *testing.T) {
	t.Setenv("KOIOTTE_CONFIG", filepath.Join(t.TempDir(), "nada.yaml"))
	c, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if c.EngineHost != "koiotte-engine" || c.APIAddr != ":8080" {
		t.Fatalf("defaults errados: %+v", c)
	}
}

func TestLoadUnknownKeyFails(t *testing.T) {
	p := writeYAML(t, "proxy:\n  management-plane:\n    api-prot: 8080\n")
	t.Setenv("KOIOTTE_CONFIG", p)
	if _, err := Load(); err == nil || !strings.Contains(err.Error(), "api-prot") {
		t.Fatalf("esperava erro de chave desconhecida, veio %v", err)
	}
}

func TestValidateCrossCheck(t *testing.T) {
	p := writeYAML(t, `
engine:
  replication:
    primary-port: 9090
manager:
  replication:
    port: 9999
`)
	errs := Validate(p)
	if len(errs) == 0 {
		t.Fatal("esperava erro de cross-check de portas de replicacao")
	}
}

func TestValidateScriptsRange(t *testing.T) {
	for _, tc := range []struct {
		name string
		yaml string
		want string
	}{
		{"pool-size zero", "engine:\n  scripts:\n    pool-size: 0\n", "engine.scripts.pool-size"},
		{"pool-size negativo", "engine:\n  scripts:\n    pool-size: -4\n", "engine.scripts.pool-size"},
		{"max-in-flight zero", "engine:\n  scripts:\n    max-in-flight: 0\n", "engine.scripts.max-in-flight"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			errs := Validate(writeYAML(t, tc.yaml))
			if len(errs) == 0 {
				t.Fatalf("esperava erro para %s", tc.name)
			}
			if !strings.Contains(errs[0], tc.want) {
				t.Fatalf("erro deveria nomear %q, veio %q", tc.want, errs[0])
			}
		})
	}
}

func TestValidateScriptsValidIsAccepted(t *testing.T) {
	errs := Validate(writeYAML(t, "engine:\n  scripts:\n    pool-size: 1\n    max-in-flight: 64\n"))
	if len(errs) != 0 {
		t.Fatalf("esperava ok, veio %v", errs)
	}
}

func TestValidateScriptsEnabledIsAccepted(t *testing.T) {
	errs := Validate(writeYAML(t, "engine:\n  scripts:\n    enabled: false\n"))
	if len(errs) != 0 {
		t.Fatalf("esperava ok, veio %v", errs)
	}
}

func TestValidateOK(t *testing.T) {
	p := writeYAML(t, `
version: 1
engine:
  port: 8081
  replication:
    primary-port: 9090
manager:
  replication:
    port: 9090
cluster:
  discovery: dns
  members: [koiotte-engine]
`)
	if errs := Validate(p); len(errs) != 0 {
		t.Fatalf("esperava ok, veio %v", errs)
	}
}
