package config

import (
	"bytes"
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

type platformYAML struct {
	Version *int `yaml:"version"`
	Shared  *struct {
		Paths *struct {
			Artifacts   *string `yaml:"artifacts"`
			Templates   *string `yaml:"templates"`
			Index       *string `yaml:"index"`
			Definitions *string `yaml:"definitions"`
		} `yaml:"paths"`
	} `yaml:"shared"`
	Engine *struct {
		Port      *int     `yaml:"port"`
		Cors      []string `yaml:"cors"`
		Protocols []string `yaml:"protocols"`
		Artifacts *struct {
			Prefault *bool `yaml:"prefault"`
		} `yaml:"artifacts"`
		Lucene *struct {
			RefreshIntervalMs *int `yaml:"refresh-interval-ms"`
			WorkerPoolSize    *int `yaml:"worker-pool-size"`
		} `yaml:"lucene"`
		Scripts *struct {
			Enabled     *bool `yaml:"enabled"`
			PoolSize    *int  `yaml:"pool-size"`
			MaxInFlight *int  `yaml:"max-in-flight"`
		} `yaml:"scripts"`
		Replication *struct {
			Enabled     *bool   `yaml:"enabled"`
			PrimaryHost *string `yaml:"primary-host"`
			PrimaryPort *int    `yaml:"primary-port"`
		} `yaml:"replication"`
	} `yaml:"engine"`
	Manager *struct {
		Port        *int     `yaml:"port"`
		Cors        []string `yaml:"cors"`
		Replication *struct {
			Enabled         *bool `yaml:"enabled"`
			Port            *int  `yaml:"port"`
			FlushIntervalMs *int  `yaml:"flush-interval-ms"`
		} `yaml:"replication"`
		Lucene *struct {
			CommitOnEveryUpdate *bool `yaml:"commit-on-every-update"`
			BatchSize           *int  `yaml:"batch-size"`
		} `yaml:"lucene"`
	} `yaml:"manager"`
	Cluster *struct {
		Enabled    *bool    `yaml:"enabled"`
		Name       *string  `yaml:"name"`
		Discovery  *string  `yaml:"discovery"`
		Members    []string `yaml:"members"`
		ConfigFile *string  `yaml:"config-file"`
	} `yaml:"cluster"`
	Proxy *struct {
		MP *mpYAML `yaml:"management-plane"`
	} `yaml:"proxy"`
	Kafka *struct {
		BootstrapServers *string `yaml:"bootstrap-servers"`
		Connect          *struct {
			RestPort   *int    `yaml:"rest-port"`
			PluginPath *string `yaml:"plugin-path"`
			Sink       *struct {
				DLQTopic *string `yaml:"dlq-topic"`
			} `yaml:"sink"`
			Source *struct {
				QueueCapacity  *int `yaml:"queue-capacity"`
				OfferTimeoutMs *int `yaml:"offer-timeout-ms"`
			} `yaml:"source"`
		} `yaml:"connect"`
	} `yaml:"kafka"`
}

func Validate(path string) []string {
	data, err := os.ReadFile(path)
	if err != nil {
		return []string{fmt.Sprintf("não consegui ler %s: %v", path, err)}
	}
	dec := yaml.NewDecoder(bytes.NewReader(data))
	dec.KnownFields(true)
	var p platformYAML
	if err := dec.Decode(&p); err != nil {
		return []string{fmt.Sprintf("schema inválido: %v", err)}
	}

	var errs []string
	if p.Version != nil && *p.Version != 1 {
		errs = append(errs, fmt.Sprintf("version %d não suportada (suportada: 1)", *p.Version))
	}
	if p.Cluster != nil && p.Cluster.Discovery != nil {
		switch *p.Cluster.Discovery {
		case "dns", "kubernetes", "static":
		default:
			errs = append(errs, fmt.Sprintf("cluster.discovery %q inválido (dns|kubernetes|static)", *p.Cluster.Discovery))
		}
	}
	if p.Cluster != nil && p.Cluster.Discovery != nil && *p.Cluster.Discovery != "" &&
		len(p.Cluster.Members) == 0 && (p.Cluster.ConfigFile == nil || *p.Cluster.ConfigFile == "") {
		errs = append(errs, "cluster.members vazio sem cluster.config-file")
	}
	if p.Engine != nil && p.Engine.Scripts != nil {
		if s := p.Engine.Scripts.PoolSize; s != nil && *s < 1 {
			errs = append(errs, fmt.Sprintf("engine.scripts.pool-size deve ser >= 1 (recebido: %d)", *s))
		}
		if s := p.Engine.Scripts.MaxInFlight; s != nil && *s < 1 {
			errs = append(errs, fmt.Sprintf("engine.scripts.max-in-flight deve ser >= 1 (recebido: %d)", *s))
		}
	}
	if p.Engine != nil && p.Engine.Replication != nil && p.Engine.Replication.PrimaryPort != nil &&
		p.Manager != nil && p.Manager.Replication != nil && p.Manager.Replication.Port != nil &&
		*p.Engine.Replication.PrimaryPort != *p.Manager.Replication.Port {
		errs = append(errs, fmt.Sprintf(
			"engine.replication.primary-port (%d) != manager.replication.port (%d)",
			*p.Engine.Replication.PrimaryPort, *p.Manager.Replication.Port))
	}
	return errs
}
