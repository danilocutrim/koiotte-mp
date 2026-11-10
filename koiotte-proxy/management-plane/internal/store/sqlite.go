package store

import (
	"database/sql"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

func OpenSQLite(dsn string) (*SQLStore, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	if _, err := db.Exec("PRAGMA foreign_keys=ON;"); err != nil {
		return nil, err
	}
	s := &SQLStore{
		db: db,
		ph: func(int) string { return "?" },
		isUnique: func(err error) bool {
			return strings.Contains(err.Error(), "UNIQUE constraint failed")
		},
	}
	if err := s.migrate(); err != nil {
		return nil, err
	}
	return s, nil
}

func dollar(n int) string { return "$" + strconv.Itoa(n) }
