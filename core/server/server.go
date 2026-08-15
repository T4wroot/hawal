package server

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

type ServerConfig struct {
	BindAddr      string   // e.g. "0.0.0.0:3090"
	Ports         []string // e.g. ["443=127.0.0.1:443", "2083=127.0.0.1:2083"]
	Token         string
	EnablePadding bool
	NoDelay       bool
}

type Server struct {
	config    ServerConfig
	crypto    *transport.CryptoManager
	listeners []net.Listener
	mu        sync.Mutex
	session   *mux.Session
}

func NewServer(cfg ServerConfig) (*Server, error) {
	crypto, err := transport.NewCryptoManager(cfg.Token)
	if err != nil {
		return nil, err
	}
	return &Server{
		config: cfg,
		crypto: crypto,
	}, nil
}

func (s *Server) Start() error {
	coreListener, err := net.Listen("tcp", s.config.BindAddr)
	if err != nil {
		return fmt.Errorf("failed to listen on core port %s: %w", s.config.BindAddr, err)
	}
	defer coreListener.Close()

	log.Printf("[Hawal-Core] 🚀 Server core listening on %s", s.config.BindAddr)

	for {
		conn, err := coreListener.Accept()
		if err != nil {
			log.Printf("[Hawal-Core] Accept error: %v", err)
			continue
		}

		if tcpConn, ok := conn.(*net.TCPConn); ok && s.config.NoDelay {
			_ = tcpConn.SetNoDelay(true)
			_ = tcpConn.SetKeepAlive(true)
			_ = tcpConn.SetKeepAlivePeriod(30 * time.Second)
		}

		go s.handleIncomingTransport(conn)
	}
}

func (s *Server) handleIncomingTransport(conn net.Conn) {
	// Perform stealth handshake verification
	if err := transport.PerformServerHandshake(conn, s.crypto, s.config.Token); err != nil {
		log.Printf("[Hawal-Core] ⚠️ Handshake failed from %s: %v (Treating as active probe)", conn.RemoteAddr(), err)
		transport.HandleActiveProbe(conn)
		return
	}

	log.Printf("[Hawal-Core] ⚡ Authenticated client connected from %s", conn.RemoteAddr())

	s.mu.Lock()
	if s.session != nil {
		s.session.Close()
	}
	// Close any previous port listeners before opening new
	for _, l := range s.listeners {
		_ = l.Close()
	}
	s.listeners = nil

	session := mux.NewSession(conn, s.crypto, s.config.EnablePadding, true)
	s.session = session
	s.mu.Unlock()

	// Start listeners on forwarded ports
	s.startForwardedListeners(session)
}

func (s *Server) startForwardedListeners(session *mux.Session) {
	for _, portRule := range s.config.Ports {
		parts := strings.Split(portRule, "=")
		listenPort := parts[0]
		listenAddr := "0.0.0.0:" + listenPort

		l, err := net.Listen("tcp", listenAddr)
		if err != nil {
			log.Printf("[Hawal-Core] ❌ Failed to bind forward port %s: %v", listenAddr, err)
			continue
		}

		s.mu.Lock()
		s.listeners = append(s.listeners, l)
		s.mu.Unlock()

		log.Printf("[Hawal-Core] 🟢 Listening for user traffic on port %s", listenPort)
		go s.forwardPortLoop(l, listenPort, session)
	}
}

func (s *Server) forwardPortLoop(l net.Listener, port string, session *mux.Session) {
	defer l.Close()

	for {
		userConn, err := l.Accept()
		if err != nil {
			return
		}

		if tcpConn, ok := userConn.(*net.TCPConn); ok && s.config.NoDelay {
			_ = tcpConn.SetNoDelay(true)
		}

		go s.pipeUserConn(userConn, port, session)
	}
}

func (s *Server) pipeUserConn(userConn net.Conn, port string, session *mux.Session) {
	defer userConn.Close()

	stream, err := session.OpenStream(port)
	if err != nil {
		return
	}
	defer stream.Close()

	var wg sync.WaitGroup
	wg.Add(2)

	// User -> Stream
	go func() {
		defer wg.Done()
		buf := mux.BufferPool.Get().([]byte)
		defer mux.BufferPool.Put(buf)
		_, _ = io.CopyBuffer(stream, userConn, buf)
		_ = stream.Close()
	}()

	// Stream -> User
	go func() {
		defer wg.Done()
		buf := mux.BufferPool.Get().([]byte)
		defer mux.BufferPool.Put(buf)
		_, _ = io.CopyBuffer(userConn, stream, buf)
		_ = userConn.Close()
	}()

	wg.Wait()
}
