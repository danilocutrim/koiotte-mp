package config

import (
	"fmt"
)

type Config struct {
	Driver     string
	DSN        string
	APIAddr    string
	XDSAddr    string
	EngineHost string
	EnginePort int
}

func Load() (Config, error) {
	c := Config{
		Driver:     "sqlite",
		DSN:        "file:koiotte-proxy.db?_pragma=busy_timeout(5000)",
		APIAddr:    ":8080",
		XDSAddr:    ":18000",
		EngineHost: "koiotte-engine",
		EnginePort: 8081,
	}

	mp, err := loadYAML(configPath())
	if err != nil {
		return Config{}, err
	}
	if mp != nil {
		if mp.APIPort != nil {
			c.APIAddr = fmt.Sprintf(":%d", *mp.APIPort)
		}
		if mp.XDSPort != nil {
			c.XDSAddr = fmt.Sprintf(":%d", *mp.XDSPort)
		}
		if mp.EngineHost != nil {
			c.EngineHost = *mp.EngineHost
		}
		if mp.EnginePort != nil {
			c.EnginePort = *mp.EnginePort
		}
		if mp.Database != nil {
			if mp.Database.Driver != nil {
				c.Driver = *mp.Database.Driver
			}
			if mp.Database.DSN != nil {
				c.DSN = *mp.Database.DSN
			}
		}
	}
	return c, nil
}
