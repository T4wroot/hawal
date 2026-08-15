package mux

import (
	"errors"
	"io"
	"net"
	"sync"
	"time"
)

// Stream represents a multiplexed virtual stream that implements net.Conn
type Stream struct {
	id         uint32
	targetPort string // Target port for client dispatch
	session    *Session
	readChan   chan []byte
	readBuf    []byte
	closeOnce  sync.Once
	closed     bool
	mu         sync.Mutex
}

func newStream(id uint32, targetPort string, session *Session) *Stream {
	return &Stream{
		id:         id,
		targetPort: targetPort,
		session:    session,
		readChan:   make(chan []byte, 128),
	}
}

func (s *Stream) ID() uint32 {
	return s.id
}

func (s *Stream) TargetPort() string {
	return s.targetPort
}

func (s *Stream) Read(b []byte) (int, error) {
	if len(s.readBuf) > 0 {
		n := copy(b, s.readBuf)
		s.readBuf = s.readBuf[n:]
		return n, nil
	}

	chunk, ok := <-s.readChan
	if !ok {
		return 0, io.EOF
	}

	n := copy(b, chunk)
	if n < len(chunk) {
		s.readBuf = chunk[n:]
	}
	return n, nil
}

func (s *Stream) Write(b []byte) (int, error) {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return 0, errors.New("stream closed")
	}
	s.mu.Unlock()

	return s.session.writeStreamData(s.id, b)
}

func (s *Stream) Close() error {
	s.closeOnce.Do(func() {
		s.mu.Lock()
		s.closed = true
		s.mu.Unlock()
		s.session.closeStream(s.id)
	})
	return nil
}

func (s *Stream) LocalAddr() net.Addr                { return s.session.LocalAddr() }
func (s *Stream) RemoteAddr() net.Addr               { return s.session.RemoteAddr() }
func (s *Stream) SetDeadline(t time.Time) error      { return nil }
func (s *Stream) SetReadDeadline(t time.Time) error  { return nil }
func (s *Stream) SetWriteDeadline(t time.Time) error { return nil }
