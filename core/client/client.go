package client

import (
	"fmt"
	"io"
	"log"
	"net"
	"strings"
	"sync"
	"time"

	"github.com/T4wroot/hawal/core/mux"
	"github.com/T4wroot/hawal/core/transport"
)

type ClientConfig struct {
	ConnectAddr   string   // e.g. "5.202.7.123:3090"
	Ports         []string // e.g. ["443=127.0.0.1:443", "2083=127.0.0.1:2083"]
	Token         string
	EnablePadding bool
	NoDelay       bool
}

type Client struct {
	config    ClientConfig
	crypto    *transport.CryptoManager
	portMap   map[string]string
	portMapMu sync.RWMutex
}

func NewClient(cfg ClientConfig) (*Client, error) {
	crypto, err := transport.NewCryptoManager(cfg.Token)
	if err != nil {
		return nil, err
	}

	pMap := make(map[string]string)
	for _, rule := range cfg.Ports {
		parts := strings.Split(rule, "=")
		if len(parts) == 2 {
			pMap[parts[0]] = parts[1]
		} else if len(parts) == 1 {
			pMap[parts[0]] = "127.0.0.1:" + parts[0]
		}
	}

	return &Client{
		config:  cfg,
		crypto:  crypto,
		portMap: pMap,
	}, nil
}

func (c *Client) Start() {
	for {
		log.Printf("[Hawal-Core] 🔌 Connecting to server at %s...", c.config.ConnectAddr)
		if err := c.connectAndServe(); err != nil {
			log.Printf("[Hawal-Core] ⚠️ Connection dropped: %v. Reconnecting in 3s...", err)
			time.Sleep(3 * time.Second)
		}
	}
}

func (c *Client) connectAndServe() error {
	conn, err := net.DialTimeout("tcp", c.config.ConnectAddr, 10*time.Second)
	if err != nil {
		return err
	}
	defer conn.Close()

	if tcpConn, ok := conn.(*net.TCPConn); ok && c.config.NoDelay {
		_ = tcpConn.SetNoDelay(true)
		_ = tcpConn.SetKeepAlive(true)
		_ = tcpConn.SetKeepAlivePeriod(30 * time.Second)
	}

	if err := transport.PerformClientHandshake(conn, c.crypto, c.config.Token); err != nil {
		return fmt.Errorf("stealth handshake failed: %w", err)
	}

	log.Printf("[Hawal-Core] 🟢 Stealth tunnel established to %s", c.config.ConnectAddr)

	session := mux.NewSession(conn, c.crypto, c.config.EnablePadding, false)
	defer session.Close()

	for {
		stream, err := session.AcceptStream()
		if err != nil {
			return err
		}

		go c.handleIncomingStream(stream)
	}
}

func (c *Client) handleIncomingStream(stream *mux.Stream) {
	defer stream.Close()

	targetPort := stream.TargetPort()
	c.portMapMu.RLock()
	localTarget, exists := c.portMap[targetPort]
	c.portMapMu.RUnlock()

	if !exists {
		localTarget = "127.0.0.1:" + targetPort
	}

	localConn, err := net.DialTimeout("tcp", localTarget, 5*time.Second)
	if err != nil {
		log.Printf("[Hawal-Core] ❌ Failed to dial local target %s: %v", localTarget, err)
		return
	}
	defer localConn.Close()

	if tcpConn, ok := localConn.(*net.TCPConn); ok && c.config.NoDelay {
		_ = tcpConn.SetNoDelay(true)
	}

	var wg sync.WaitGroup
	wg.Add(2)

	// Stream -> Local Target
	go func() {
		defer wg.Done()
		buf := mux.BufferPool.Get().([]byte)
		defer mux.BufferPool.Put(buf)
		_, _ = io.CopyBuffer(localConn, stream, buf)
		_ = localConn.Close()
	}()

	// Local Target -> Stream
	go func() {
		defer wg.Done()
		buf := mux.BufferPool.Get().([]byte)
		defer mux.BufferPool.Put(buf)
		_, _ = io.CopyBuffer(stream, localConn, buf)
		_ = stream.Close()
	}()

	wg.Wait()
}
