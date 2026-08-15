package mux

import (
	"errors"
	"io"
	"net"
	"sync"
	"sync/atomic"
	"time"

	"github.com/T4wroot/hawal/core/transport"
)

var BufferPool = sync.Pool{
	New: func() interface{} {
		b := make([]byte, 32*1024)
		return b
	},
}

type Session struct {
	conn          net.Conn
	crypto        *transport.CryptoManager
	enablePadding bool
	isServer      bool

	nextStreamID uint32
	streams      map[uint32]*Stream
	streamsMu    sync.RWMutex

	acceptChan chan *Stream
	writeMu    sync.Mutex
	closed     bool
	closeOnce  sync.Once
}

func NewSession(conn net.Conn, crypto *transport.CryptoManager, enablePadding bool, isServer bool) *Session {
	s := &Session{
		conn:          conn,
		crypto:        crypto,
		enablePadding: enablePadding,
		isServer:      isServer,
		streams:       make(map[uint32]*Stream),
		acceptChan:    make(chan *Stream, 256),
	}
	if isServer {
		s.nextStreamID = 1 // Server starts stream IDs from 1
	} else {
		s.nextStreamID = 2 // Client starts stream IDs from 2
	}

	go s.readLoop()
	go s.pingLoop()
	return s
}

func (s *Session) LocalAddr() net.Addr  { return s.conn.LocalAddr() }
func (s *Session) RemoteAddr() net.Addr { return s.conn.RemoteAddr() }

func (s *Session) OpenStream(targetPort string) (*Stream, error) {
	s.streamsMu.Lock()
	if s.closed {
		s.streamsMu.Unlock()
		return nil, errors.New("session closed")
	}
	streamID := atomic.AddUint32(&s.nextStreamID, 2)
	stream := newStream(streamID, targetPort, s)
	s.streams[streamID] = stream
	s.streamsMu.Unlock()

	// Send FrameStreamOpen with target port in payload
	openFrame := &transport.Frame{
		Type:     transport.FrameStreamOpen,
		StreamID: streamID,
		Payload:  []byte(targetPort),
	}

	s.writeMu.Lock()
	err := transport.WriteFrame(s.conn, s.crypto, openFrame, s.enablePadding)
	s.writeMu.Unlock()
	if err != nil {
		s.closeStream(streamID)
		return nil, err
	}
	return stream, nil
}

func (s *Session) AcceptStream() (*Stream, error) {
	stream, ok := <-s.acceptChan
	if !ok {
		return nil, io.EOF
	}
	return stream, nil
}

func (s *Session) writeStreamData(streamID uint32, data []byte) (int, error) {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()

	if s.closed {
		return 0, errors.New("session closed")
	}

	total := len(data)
	offset := 0

	for offset < total {
		chunkSize := total - offset
		if chunkSize > transport.MaxPayloadSize {
			chunkSize = transport.MaxPayloadSize
		}

		frame := &transport.Frame{
			Type:     transport.FrameData,
			StreamID: streamID,
			Payload:  data[offset : offset+chunkSize],
		}

		if err := transport.WriteFrame(s.conn, s.crypto, frame, s.enablePadding); err != nil {
			return offset, err
		}
		offset += chunkSize
	}
	return total, nil
}

func (s *Session) closeStream(streamID uint32) {
	s.streamsMu.Lock()
	stream, exists := s.streams[streamID]
	if exists {
		delete(s.streams, streamID)
		close(stream.readChan)
	}
	s.streamsMu.Unlock()

	if exists {
		s.writeMu.Lock()
		closeFrame := &transport.Frame{
			Type:     transport.FrameStreamClose,
			StreamID: streamID,
		}
		_ = transport.WriteFrame(s.conn, s.crypto, closeFrame, s.enablePadding)
		s.writeMu.Unlock()
	}
}

func (s *Session) readLoop() {
	defer s.Close()

	for {
		frame, err := transport.ReadFrame(s.conn, s.crypto)
		if err != nil {
			return
		}

		switch frame.Type {
		case transport.FrameStreamOpen:
			targetPort := string(frame.Payload)
			stream := newStream(frame.StreamID, targetPort, s)
			s.streamsMu.Lock()
			s.streams[frame.StreamID] = stream
			s.streamsMu.Unlock()

			select {
			case s.acceptChan <- stream:
			default:
				// Queue full, drop stream
				s.closeStream(frame.StreamID)
			}

		case transport.FrameData:
			s.streamsMu.RLock()
			stream, exists := s.streams[frame.StreamID]
			s.streamsMu.RUnlock()

			if exists {
				select {
				case stream.readChan <- frame.Payload:
				case <-time.After(5 * time.Second):
					// Stream blocked or dead
					s.closeStream(frame.StreamID)
				}
			}

		case transport.FrameStreamClose:
			s.streamsMu.Lock()
			if stream, exists := s.streams[frame.StreamID]; exists {
				delete(s.streams, frame.StreamID)
				close(stream.readChan)
			}
			s.streamsMu.Unlock()

		case transport.FramePing:
			s.writeMu.Lock()
			_ = transport.WriteFrame(s.conn, s.crypto, &transport.Frame{Type: transport.FramePong}, s.enablePadding)
			s.writeMu.Unlock()

		case transport.FramePong:
			// Heartbeat acknowledged
		}
	}
}

func (s *Session) pingLoop() {
	ticker := time.NewTicker(25 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		s.writeMu.Lock()
		if s.closed {
			s.writeMu.Unlock()
			return
		}
		_ = transport.WriteFrame(s.conn, s.crypto, &transport.Frame{Type: transport.FramePing}, s.enablePadding)
		s.writeMu.Unlock()
	}
}

func (s *Session) Close() error {
	s.closeOnce.Do(func() {
		s.streamsMu.Lock()
		s.closed = true
		for id, st := range s.streams {
			delete(s.streams, id)
			close(st.readChan)
		}
		s.streamsMu.Unlock()

		close(s.acceptChan)
		_ = s.conn.Close()
	})
	return nil
}
