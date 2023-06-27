package chanwriter

type Writer struct {
	c chan<- string
}

func New(ch chan<- string) *Writer {
	return &Writer{
		c: ch,
	}
}

func (cw *Writer) Write(p []byte) (n int, err error) {
	str := string(p)
	cw.c <- str
	return len(p), nil
}
