package transport

import (
	"bytes"
	"fmt"
	"net"
	"time"
)

// HandleActiveProbe handles probing scanner connections by returning a standard Nginx 404 page
func HandleActiveProbe(conn net.Conn) {
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(5 * time.Second))

	response := "HTTP/1.1 404 Not Found\r\n" +
		"Server: nginx/1.24.0 (Ubuntu)\r\n" +
		"Date: " + time.Now().UTC().Format(time.RFC1123) + "\r\n" +
		"Content-Type: text/html\r\n" +
		"Content-Length: 162\r\n" +
		"Connection: close\r\n\r\n" +
		"<html>\r\n<head><title>404 Not Found</title></head>\r\n" +
		"<body>\r\n<center><h1>404 Not Found</h1></center>\r\n" +
		"<hr><center>nginx/1.24.0 (Ubuntu)</center>\r\n" +
		"</body>\r\n</html>\r\n"

	_, _ = conn.Write([]byte(response))
}

// PerformClientHandshake sends an initial obfuscated handshake frame
func PerformClientHandshake(conn net.Conn, crypto *CryptoManager, token string) error {
	hsFrame := &Frame{
		Type:     FrameHandshake,
		StreamID: 0,
		Payload:  []byte(fmt.Sprintf("HWL_HS:%s", token)),
	}
	if err := WriteFrame(conn, crypto, hsFrame, true); err != nil {
		return err
	}

	ackFrame, err := ReadFrame(conn, crypto)
	if err != nil {
		return err
	}
	if ackFrame.Type != FrameHandshakeAck {
		return fmt.Errorf("handshake rejected, type: %d", ackFrame.Type)
	}
	return nil
}

// PerformServerHandshake verifies client's handshake frame and responds with Ack
func PerformServerHandshake(conn net.Conn, crypto *CryptoManager, expectedToken string) error {
	_ = conn.SetReadDeadline(time.Now().Add(10 * time.Second))
	defer func() { _ = conn.SetReadDeadline(time.Time{}) }()

	frame, err := ReadFrame(conn, crypto)
	if err != nil {
		return err
	}

	expectedPayload := []byte(fmt.Sprintf("HWL_HS:%s", expectedToken))
	if frame.Type != FrameHandshake || !bytes.Equal(frame.Payload, expectedPayload) {
		return fmt.Errorf("unauthorized handshake payload")
	}

	ackFrame := &Frame{
		Type:     FrameHandshakeAck,
		StreamID: 0,
		Payload:  []byte("OK"),
	}
	return WriteFrame(conn, crypto, ackFrame, true)
}
