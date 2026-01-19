// Package hashing provides file hashing utilities for ROM identification.
package hashing

import (
	"crypto/md5"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"hash/crc32"
	"io"
	"os"
)

// FileHashes contains all computed hashes for a file.
type FileHashes struct {
	MD5    string
	SHA1   string
	CRC32  string
	SHA256 string
}

// ComputeFileHashes computes all hashes for a file.
func ComputeFileHashes(path string) (*FileHashes, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("opening file: %w", err)
	}
	defer file.Close()

	return ComputeReaderHashes(file)
}

// ComputeReaderHashes computes all hashes from a reader.
func ComputeReaderHashes(r io.Reader) (*FileHashes, error) {
	md5Hash := md5.New()
	sha1Hash := sha1.New()
	sha256Hash := sha256.New()
	crc32Hash := crc32.NewIEEE()

	// Create a multi-writer to compute all hashes in one pass
	multiWriter := io.MultiWriter(md5Hash, sha1Hash, sha256Hash, crc32Hash)

	if _, err := io.Copy(multiWriter, r); err != nil {
		return nil, fmt.Errorf("computing hashes: %w", err)
	}

	return &FileHashes{
		MD5:    hex.EncodeToString(md5Hash.Sum(nil)),
		SHA1:   hex.EncodeToString(sha1Hash.Sum(nil)),
		CRC32:  fmt.Sprintf("%08x", crc32Hash.Sum32()),
		SHA256: hex.EncodeToString(sha256Hash.Sum(nil)),
	}, nil
}

// ComputeMD5 computes the MD5 hash of a file.
func ComputeMD5(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("opening file: %w", err)
	}
	defer file.Close()

	return ComputeMD5FromReader(file)
}

// ComputeMD5FromReader computes the MD5 hash from a reader.
func ComputeMD5FromReader(r io.Reader) (string, error) {
	h := md5.New()
	if _, err := io.Copy(h, r); err != nil {
		return "", fmt.Errorf("computing MD5: %w", err)
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// ComputeSHA1 computes the SHA1 hash of a file.
func ComputeSHA1(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("opening file: %w", err)
	}
	defer file.Close()

	return ComputeSHA1FromReader(file)
}

// ComputeSHA1FromReader computes the SHA1 hash from a reader.
func ComputeSHA1FromReader(r io.Reader) (string, error) {
	h := sha1.New()
	if _, err := io.Copy(h, r); err != nil {
		return "", fmt.Errorf("computing SHA1: %w", err)
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// ComputeCRC32 computes the CRC32 hash of a file.
func ComputeCRC32(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("opening file: %w", err)
	}
	defer file.Close()

	return ComputeCRC32FromReader(file)
}

// ComputeCRC32FromReader computes the CRC32 hash from a reader.
func ComputeCRC32FromReader(r io.Reader) (string, error) {
	h := crc32.NewIEEE()
	if _, err := io.Copy(h, r); err != nil {
		return "", fmt.Errorf("computing CRC32: %w", err)
	}
	return fmt.Sprintf("%08x", h.Sum32()), nil
}

// ComputeSHA256 computes the SHA256 hash of a file.
func ComputeSHA256(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("opening file: %w", err)
	}
	defer file.Close()

	return ComputeSHA256FromReader(file)
}

// ComputeSHA256FromReader computes the SHA256 hash from a reader.
func ComputeSHA256FromReader(r io.Reader) (string, error) {
	h := sha256.New()
	if _, err := io.Copy(h, r); err != nil {
		return "", fmt.Errorf("computing SHA256: %w", err)
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// ComputeMD5String computes the MD5 hash of a string.
func ComputeMD5String(s string) string {
	h := md5.Sum([]byte(s))
	return hex.EncodeToString(h[:])
}

// ComputeSHA1String computes the SHA1 hash of a string.
func ComputeSHA1String(s string) string {
	h := sha1.Sum([]byte(s))
	return hex.EncodeToString(h[:])
}
