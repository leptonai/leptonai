package chanwriter

import "testing"

func TestWriter(t *testing.T) {
	ch := make(chan string, 2)
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

	if cw.Tail(0) != "" {
		t.Errorf("cw.Tail(0) returned %s, want \"\"", cw.Tail(0))
	}
	if cw.Tail(1) != "world" {
		t.Errorf("cw.Tail(1) returned %s, want \"world\"", cw.Tail(1))
	}
	if cw.Tail(2) != "hello\nworld" {
		t.Errorf("cw.Tail(2) returned %s, want \"hello\nworld\"", cw.Tail(2))
	}
	if cw.Tail(100) != "hello\nworld" {
		t.Errorf("cw.Tail(100) returned %s, want \"hello\nworld\"", cw.Tail(100))
	}
	if cw.Tail(-1) != "hello\nworld" {
		t.Errorf("cw.Tail(-1) returned %s, want \"hello\nworld\"", cw.Tail(-1))
	}
}
