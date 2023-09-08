package chanwriter

import (
	"strings"
	"sync"
)

type Writer struct {
	c chan<- string

	linesMu sync.RWMutex
	lines   []string
}

func New(ch chan<- string) *Writer {
	return &Writer{
		c:     ch,
		lines: make([]string, 0, 5000),
	}
}

func (cw *Writer) Write(p []byte) (n int, err error) {
	str := string(p)

	cw.linesMu.Lock()
	cw.lines = append(cw.lines, str)
	if len(cw.lines) > 5000 {
		cw.lines = cw.lines[:5000]
	}
	cw.linesMu.Unlock()

	cw.c <- str
	return len(p), nil
}

func (cw *Writer) Tail(n int) string {
	cw.linesMu.RLock()
	defer cw.linesMu.RUnlock()

	linesN := len(cw.lines)
	if n == 0 || linesN == 0 {
		return ""
	}

	start := linesN - n
	if n < 0 || n > linesN {
		start = 0
	}

	return strings.Join(cw.lines[start:], "\n")
}
