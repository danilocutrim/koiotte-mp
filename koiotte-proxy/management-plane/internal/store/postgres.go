package store

import (
	"database/sql"

	"github.com/jackc/pgx/v5/pgconn"
	_ "github.com/jackc/pgx/v5/stdlib"
)

func OpenPostgres(dsn string) (*SQLStore, error) {
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	s := &SQLStore{
		db: db,
		ph: dollar,
		isUnique: func(err error) bool {
			var pgErr *pgconn.PgError
			if e, ok := err.(*pgconn.PgError); ok {
				pgErr = e
			}
			return pgErr != nil && pgErr.Code == "23505"
		},
	}
	if err := s.migrate(); err != nil {
		return nil, err
	}
	return s, nil
}
