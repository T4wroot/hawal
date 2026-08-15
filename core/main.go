package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/T4wroot/hawal/core/client"
	"github.com/T4wroot/hawal/core/server"
)

type ConfigFile struct {
	Mode          string   `json:"mode"`
	BindAddr      string   `json:"bind_addr"`
	ConnectAddr   string   `json:"connect_addr"`
	Ports         []string `json:"ports"`
	Token         string   `json:"token"`
	EnablePadding bool     `json:"enable_padding"`
	NoDelay       bool     `json:"nodelay"`
}

func main() {
	mode := flag.String("mode", "", "Execution mode: 'server' or 'client'")
	bindAddr := flag.String("listen", "", "Core transport listen address for server (e.g. 0.0.0.0:3090)")
	connectAddr := flag.String("connect", "", "Server address for client to connect to (e.g. 5.202.7.123:3090)")
	portsFlag := flag.String("ports", "", "Comma-separated port forward rules (e.g. 443=127.0.0.1:443,2083=127.0.0.1:2083)")
	token := flag.String("token", "", "Shared authentication and encryption secret")
	enablePadding := flag.Bool("padding", true, "Enable dynamic random noise padding (Anti-DPI)")
	noDelay := flag.Bool("nodelay", true, "Enable TCP_NODELAY for ultra-low latency")
	configPath := flag.String("config", "", "Path to JSON configuration file")
	flag.Parse()

	cfg := ConfigFile{
		Mode:          *mode,
		BindAddr:      *bindAddr,
		ConnectAddr:   *connectAddr,
		Token:         *token,
		EnablePadding: *enablePadding,
		NoDelay:       *noDelay,
	}

	if *portsFlag != "" {
		cfg.Ports = strings.Split(*portsFlag, ",")
	}

	if *configPath != "" {
		data, err := os.ReadFile(*configPath)
		if err != nil {
			log.Fatalf("Failed to read config file: %v", err)
		}
		if err := json.Unmarshal(data, &cfg); err != nil {
			log.Fatalf("Failed to parse config file: %v", err)
		}
	}

	if cfg.Token == "" {
		log.Fatalf("Authentication token is required (-token or in config)")
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	fmt.Println("⚡ ===============================================")
	fmt.Println("🚀 Hawal Stealth Core (هه‌واڵ) v1.0.0")
	fmt.Println("🔒 Engine: Go Multi-Stream Zero-Alloc Anti-DPI")
	fmt.Printf("🎯 Mode: %s\n", cfg.Mode)
	fmt.Println("===============================================")

	switch cfg.Mode {
	case "server":
		if cfg.BindAddr == "" {
			log.Fatalf("-listen address is required for server mode")
		}
		srv, err := server.NewServer(server.ServerConfig{
			BindAddr:      cfg.BindAddr,
			Ports:         cfg.Ports,
			Token:         cfg.Token,
			EnablePadding: cfg.EnablePadding,
			NoDelay:       cfg.NoDelay,
		})
		if err != nil {
			log.Fatalf("Server initialization failed: %v", err)
		}

		go func() {
			if err := srv.Start(); err != nil {
				log.Fatalf("Server exited with error: %v", err)
			}
		}()

	case "client":
		if cfg.ConnectAddr == "" {
			log.Fatalf("-connect address is required for client mode")
		}
		cli, err := client.NewClient(client.ClientConfig{
			ConnectAddr:   cfg.ConnectAddr,
			Ports:         cfg.Ports,
			Token:         cfg.Token,
			EnablePadding: cfg.EnablePadding,
			NoDelay:       cfg.NoDelay,
		})
		if err != nil {
			log.Fatalf("Client initialization failed: %v", err)
		}

		go cli.Start()

	default:
		log.Fatalf("Invalid mode '%s'. Use -mode=server or -mode=client", cfg.Mode)
	}

	<-sigChan
	fmt.Println("\n🛑 Shutting down Hawal Core cleanly...")
}
