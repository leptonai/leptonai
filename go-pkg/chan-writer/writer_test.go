package chanwriter

import "testing"

func TestWriter(t *testing.T) {
	ch := make(chan string)
	cw := New(ch)
	go func() {
		if _, err := cw.Write([]byte("hello")); err != nil {
			t.Errorf("ChanWriter.Write([]byte(\"hello\")) = %v; want nil", err)
		}
		if _, err := cw.Write([]byte("world")); err != nil {
			t.Errorf("ChanWriter.Write([]byte(\"world\")) = %v; want nil", err)
		}
	}()
	result := <-ch
	if result != "hello" {
		t.Errorf("ChanWriter.Write([]byte(\"hello\")) = %s; want \"hello\"", result)
	}
	result = <-ch
	if result != "world" {
		t.Errorf("ChanWriter.Write([]byte(\"world\")) = %s; want \"world\"", result)
	}
}
