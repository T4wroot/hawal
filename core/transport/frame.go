package transport

import (
	"crypto/rand"
	"encoding/binary"
	"errors"
	"io"
	"math/big"
)

const (
	MagicHeader = 0x48574C31 // "HWL1"

	FrameHandshake    byte = 0x01
	FrameHandshakeAck byte = 0x02
	FrameData         byte = 0x03
	FrameStreamOpen   byte = 0x04
	FrameStreamClose  byte = 0x05
	FramePing         byte = 0x06
	FramePong         byte = 0x07

	MaxPayloadSize = 32768 // 32 KB per chunk
	MaxPaddingSize = 48    // Up to 48 bytes random padding per frame
)

type Frame struct {
	Type     byte
	StreamID uint32
	Payload  []byte
}

// WriteFrame encrypts, applies dynamic noise padding, and sends a frame over the socket
func WriteFrame(w io.Writer, crypto *CryptoManager, f *Frame, enablePadding bool) error {
	payloadLen := len(f.Payload)
	padLen := 0
	if enablePadding {
		n, _ := rand.Int(rand.Reader, big.NewInt(MaxPaddingSize+1))
		padLen = int(n.Int64())
	}

	// Body to encrypt: [Payload | Random Padding]
	body := make([]byte, payloadLen+padLen)
	copy(body, f.Payload)
	if padLen > 0 {
		if _, err := io.ReadFull(rand.Reader, body[payloadLen:]); err != nil {
			return err
		}
	}

	encryptedBody, err := crypto.Encrypt(body)
	if err != nil {
		return err
	}

	// Frame header: 12 bytes
	// [Magic 4B | Type 1B | StreamID 4B | PayloadLen 2B | PadLen 1B]
	header := make([]byte, 12)
	binary.BigEndian.PutUint32(header[0:4], MagicHeader)
	header[4] = f.Type
	binary.BigEndian.PutUint32(header[5:9], f.StreamID)
	binary.BigEndian.PutUint16(header[9:11], uint16(payloadLen))
	header[11] = byte(padLen)

	if _, err := w.Write(header); err != nil {
		return err
	}
	// Write length of encrypted body (4 bytes) + encrypted body
	encLenBuf := make([]byte, 4)
	binary.BigEndian.PutUint32(encLenBuf, uint32(len(encryptedBody)))
	if _, err := w.Write(encLenBuf); err != nil {
		return err
	}
	_, err = w.Write(encryptedBody)
	return err
}

// ReadFrame reads, verifies magic bytes, decrypts and extracts unpadded payload
func ReadFrame(r io.Reader, crypto *CryptoManager) (*Frame, error) {
	header := make([]byte, 12)
	if _, err := io.ReadFull(r, header); err != nil {
		return nil, err
	}

	magic := binary.BigEndian.Uint32(header[0:4])
	if magic != MagicHeader {
		return nil, errors.New("invalid magic header")
	}

	frameType := header[4]
	streamID := binary.BigEndian.Uint32(header[5:9])
	payloadLen := int(binary.BigEndian.Uint16(header[9:11]))
	padLen := int(header[11])

	encLenBuf := make([]byte, 4)
	if _, err := io.ReadFull(r, encLenBuf); err != nil {
		return nil, err
	}
	encLen := binary.BigEndian.Uint32(encLenBuf)
	if encLen > MaxPayloadSize+1024 {
		return nil, errors.New("frame length exceeds limit")
	}

	encryptedBody := make([]byte, encLen)
	if _, err := io.ReadFull(r, encryptedBody); err != nil {
		return nil, err
	}

	body, err := crypto.Decrypt(encryptedBody)
	if err != nil {
		return nil, err
	}

	if len(body) < payloadLen+padLen {
		return nil, errors.New("decrypted body shorter than header specification")
	}

	return &Frame{
		Type:     frameType,
		StreamID: streamID,
		Payload:  body[:payloadLen],
	}, nil
}
