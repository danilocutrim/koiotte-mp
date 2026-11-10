package config

import (
	"bytes"
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

const defaultConfigPath = "/etc/koiotte/koiotte.yaml"

type mpYAML struct {
	APIPort    *int    `yaml:"api-port"`
	XDSPort    *int    `yaml:"xds-port"`
	EngineHost *string `yaml:"engine-host"`
	EnginePort *int    `yaml:"engine-port"`
	Database   *struct {
		Driver *string `yaml:"driver"`
		DSN    *string `yaml:"dsn"`
	} `yaml:"database"`
}

func configPath() string {
	if p := os.Getenv("KOIOTTE_CONFIG"); p != "" {
		return p
	}
	return defaultConfigPath
}

func loadYAML(path string) (*mpYAML, error) {
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var root struct {
		Proxy struct {
			MP yaml.Node `yaml:"management-plane"`
		} `yaml:"proxy"`
	}
	if err := yaml.Unmarshal(data, &root); err != nil {
		return nil, fmt.Errorf("koiotte.yaml inválido em %s: %w", path, err)
	}
	if root.Proxy.MP.IsZero() {
		return nil, nil
	}
	raw, err := yaml.Marshal(&root.Proxy.MP)
	if err != nil {
		return nil, err
	}
	dec := yaml.NewDecoder(bytes.NewReader(raw))
	dec.KnownFields(true)
	var mp mpYAML
	if err := dec.Decode(&mp); err != nil {
		return nil, fmt.Errorf("koiotte.yaml: seção proxy.management-plane inválida: %w", err)
	}
	return &mp, nil
}
