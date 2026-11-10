//go:build integration

package store

import (
	"os"
	"testing"
)

func TestPostgres(t *testing.T) {
	dsn := os.Getenv("KP_TEST_PG_DSN")
	if dsn == "" {
		t.Skip("set KP_TEST_PG_DSN to run postgres conformance")
	}
	RunStoreConformance(t, func() Store {
		s, err := OpenPostgres(dsn)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := s.db.Exec("TRUNCATE routing_state, services, tenants CASCADE"); err != nil {
			t.Fatal(err)
		}
		return s
	})
}
