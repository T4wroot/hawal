package transport

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"errors"
	"io"
)

// CryptoManager manages session-level encryption and decryption.
type CryptoManager struct {
	aead cipher.AEAD
}

// NewCryptoManager derives a 32-byte AES key from token using SHA-256
func NewCryptoManager(token string) (*CryptoManager, error) {
	hash := sha256.Sum256([]byte(token))
	block, err := aes.NewCipher(hash[:])
	if err != nil {
		return nil, err
	}
	aead, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	return &CryptoManager{aead: aead}, nil
}

// Encrypt encrypts plaintext and appends authentication tag with random nonce
func (cm *CryptoManager) Encrypt(plaintext []byte) ([]byte, error) {
	nonce := make([]byte, cm.aead.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}
	// Result: [Nonce (12 bytes) | Ciphertext + Tag (len + 16)]
	return cm.aead.Seal(nonce, nonce, plaintext, nil), nil
}

// Decrypt extracts nonce and decrypts ciphertext
func (cm *CryptoManager) Decrypt(ciphertext []byte) ([]byte, error) {
	nonceSize := cm.aead.NonceSize()
	if len(ciphertext) < nonceSize {
		return nil, errors.New("ciphertext too short for nonce")
	}
	nonce := ciphertext[:nonceSize]
	data := ciphertext[nonceSize:]
	return cm.aead.Open(nil, nonce, data, nil)
}
