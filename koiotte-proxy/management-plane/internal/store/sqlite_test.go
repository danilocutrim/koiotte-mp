package store

import "testing"

func TestSQLite(t *testing.T) {
	RunStoreConformance(t, func() Store {
		s, err := OpenSQLite("file::memory:?cache=shared&_pragma=busy_timeout(5000)")
		if err != nil {
			t.Fatal(err)
		}
		return s
	})
}
