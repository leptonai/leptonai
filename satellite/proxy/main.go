// "proxy" implements simple TCP passthrough proxy for satellite node testing.
// Ideally, this should be done in iptables/route tables.
// Use this for quick experiments and debugging.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"
)

// go run main.go "10.0.6.220" "152.70.125.141" "10250,443,80,8080"
func main() {
	flag.Parse()

	args := flag.Args()
	if args == nil || len(args) != 3 {
		panic(fmt.Errorf("expected 3 arg, got %v", args))
	}

	localAddrs := make([]string, 0)
	for _, s := range strings.Split(args[0], ",") {
		localAddrs = append(localAddrs, strings.TrimSpace(s))
	}
	remoteAddrs := make([]string, 0)
	for _, s := range strings.Split(args[1], ",") {
		remoteAddrs = append(remoteAddrs, strings.TrimSpace(s))
	}
	if len(localAddrs) != len(remoteAddrs) {
		panic(errors.New("localAddrs and remoteAddrs must have same length"))
	}

	ports := make([]int, 0)
	for _, s := range strings.Split(args[2], ",") {
		var port int
		_, err := fmt.Sscanf(strings.TrimSpace(s), "%d", &port)
		if err != nil {
			panic(err)
		}
		ports = append(ports, port)
	}

	rootCtx, rootCancel := context.WithCancel(context.Background())
	wg := sync.WaitGroup{}
	for i, localIP := range localAddrs {
		remoteIP := remoteAddrs[i]

		for _, port := range ports {
			wg.Add(1)
			go start(rootCtx, &wg, localIP, remoteIP, port)
		}
	}

	osSig := make(chan os.Signal, 1)
	signal.Notify(osSig, syscall.SIGINT, syscall.SIGTERM)
	sig := <-osSig
	log.Printf("received os signal: %v -- closing listeners", sig)

	rootCancel()
	wg.Done()
}

// no need tls.Dial, since we only forward packets
// remote, err := tls.Dial("tcp", remoteAddr, &tls.Config{ InsecureSkipVerify: true })

func start(rootCtx context.Context, wg *sync.WaitGroup, localIP string, remoteIP string, port int) {
	defer wg.Done()

	localAddr := net.JoinHostPort(localIP, fmt.Sprint(port))
	remoteAddr := net.JoinHostPort(remoteIP, fmt.Sprint(port))

	// enable ICMP/TCP ping
	log.Printf("starting proxy listener with localAddr=%q, remoteAddr=%q", localAddr, remoteAddr)
	ln, err := net.Listen("tcp", localAddr)
	if err != nil {
		panic(err)
	}
	defer ln.Close()

	for {
		select {
		case <-rootCtx.Done():
			return
		default:
		}

		local, err := ln.Accept()
		if err != nil {
			log.Printf("failed accept local connection: %v", err)
			continue
		}

		connID := rand.Int63()
		log.Printf("[%d] accepted local conn addr %s to remote %s", connID, local.LocalAddr().String(), remoteAddr)

		if tc, ok := local.(*net.TCPConn); ok {
			if serr := tc.SetKeepAlive(true); serr != nil {
				log.Printf("[%d] failed to set keepalive for local connection: %v", connID, serr)
			} else {
				log.Printf("[%d] set keepalive for local connection", connID)
			}
		}

		dialer := &net.Dialer{
			Timeout:   15 * time.Second,
			KeepAlive: 15 * time.Second,
		}
		ctx, cancel := context.WithTimeout(rootCtx, 15*time.Second)
		remote, err := dialer.DialContext(ctx, "tcp", remoteAddr)
		cancel()
		if err != nil {
			local.Close()
			log.Printf("failed to connect to remote: %v", err)
			continue
		}

		if tc, ok := remote.(*net.TCPConn); ok {
			if serr := tc.SetKeepAlive(true); serr != nil {
				log.Printf("[%d] failed to set keepalive for remote connection: %v", connID, serr)
			} else {
				log.Printf("[%d] set keepalive for remote connection", connID)
			}
		}

		go forward(rootCtx, connID, local, remote)
	}
}

// forward data bi-directionally
func forward(rootCtx context.Context, connID int64, local net.Conn, remote net.Conn) {
	donec1, donec2 := make(chan struct{}), make(chan struct{})
	go func() {
		defer func() {
			close(donec1)
		}()

		n, err := io.Copy(local, remote)
		if err != nil {
			log.Printf("[%d] failed io.Copy remote to local: %v", connID, err)
			return
		}
		log.Printf("[%d] ok io.Copy remote to local: %d bytes", connID, n)
	}()
	go func() {
		defer func() {
			close(donec2)
		}()

		n, err := io.Copy(remote, local)
		if err != nil {
			log.Printf("[%d] failed io.Copy local to remote: %v", connID, err)
			return
		}
		log.Printf("[%d] ok io.Copy local to remote: %d bytes", connID, n)
	}()

	select {
	case <-rootCtx.Done():
		// do not block on existing goroutines
		// just close the connections
	case <-donec1:
		select {
		case <-rootCtx.Done():
		case <-donec2:
		}
	case <-donec2:
		select {
		case <-rootCtx.Done():
		case <-donec1:
		}
	}

	local.Close()
	remote.Close()

	log.Printf("[%d] closed local and remote", connID)
}
