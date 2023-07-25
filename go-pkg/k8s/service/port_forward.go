package service

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"time"

	opencost_pod "github.com/leptonai/lepton/go-pkg/k8s/pod-for-opencost/pod"
	goutil "github.com/leptonai/lepton/go-pkg/util"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/portforward"
	"k8s.io/client-go/transport/spdy"
)

// Mostly copied from https://github.com/kubecost/kubectl-cost/blob/main/pkg/query/portforward.go

type PortForwardQuerier struct {
	BaseQueryURL string
	stopCh       chan struct{}
}

func NewPortForwardQuerier(
	ctx context.Context,
	clientset *kubernetes.Clientset,
	restConfig *rest.Config,
	namespace string,
	serviceName string,
	servicePort int) (*PortForwardQuerier, error) {
	// First: find a pod to port forward to
	pods, err := getServicePods(ctx, clientset, namespace, serviceName)
	if err != nil {
		return nil, fmt.Errorf("failed to get service pods: %s", err)
	}
	if len(pods.Items) == 0 {
		return nil, fmt.Errorf("no pods for service %s in namespace %s", serviceName, namespace)
	}

	// It's possible that there can be pods matching the service which are in a
	// non-Ready (e.g. Error, Completed) state. Make sure we select a Ready pod.
	var podToForward *corev1.Pod
	for _, pod := range pods.Items {
		pod := pod
		log.Printf("checking pod readiness of pod %q", pod.Name)
		if opencost_pod.IsReady(&pod) {
			podToForward = &pod
			break
		}
	}

	if podToForward == nil {
		return nil, fmt.Errorf("couldn't find a Pod which is Ready to serve the query")
	}

	goutil.Logger.Infof("selected pod to forward %q", podToForward.Name)

	// Second: build the port forwarding config
	// https://stackoverflow.com/questions/59027739/upgrading-connection-error-in-port-forwarding-via-client-go
	reqURL := clientset.CoreV1().RESTClient().Post().
		Resource("pods").
		Namespace(namespace).
		Name(podToForward.Name).
		SubResource("portforward").URL()

	var berr, bout bytes.Buffer
	buffErr := bufio.NewWriter(&berr)
	buffOut := bufio.NewWriter(&bout)

	readyCh := make(chan struct{})
	stopCh := make(chan struct{}, 1)

	transport, upgrader, err := spdy.RoundTripperFor(restConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create round tripper for rest config: %s", err)
	}

	dialer := spdy.NewDialer(
		upgrader,
		&http.Client{Transport: transport},
		http.MethodPost,
		reqURL,
	)

	fw, err := portforward.New(
		dialer,
		[]string{fmt.Sprintf("%d:%d", 0, servicePort)},
		stopCh,
		readyCh,
		buffOut,
		buffErr,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create portfoward: %s", err)
	}

	// Third: port forward
	go func() {
		err = fw.ForwardPorts()
		if err != nil {
			panic(err)
		}
	}()

	// Fourth: wait until the port forward is ready, or we hit a timeout.
	select {
	case <-readyCh:
		break
	case <-time.After(15 * time.Second):
		return nil, fmt.Errorf("timed out (15 sec) trying to port forward")
	}

	// Confirm that we've port forwarded and allows us to discover the local forwarded port.
	// Because we specified port 0, we will have used a random, previously unused port.
	ports, err := fw.GetPorts()
	if err != nil {
		return nil, fmt.Errorf("failed to get list of forwarded ports: %s", err)
	}
	if len(ports) == 0 {
		return nil, fmt.Errorf("unexpected error: no ports forwarded")
	}

	baseQueryURL := fmt.Sprintf("http://localhost:%d", ports[0].Local)
	log.Printf("port-forward set up to base-query url %q", baseQueryURL)

	return &PortForwardQuerier{
		BaseQueryURL: baseQueryURL,
		stopCh:       stopCh,
	}, nil
}

// Stop ends the port forward session.
func (pfq *PortForwardQuerier) Stop() {
	pfq.BaseQueryURL = ""
	close(pfq.stopCh)
}

// QueryGet relies on a live port-forward session to execute a GET request
// against a forwarded service at the given path with the given params.
func (pfq *PortForwardQuerier) QueryGet(ctx context.Context, path string, params map[string]string) ([]byte, error) {
	if pfq.BaseQueryURL == "" {
		return nil, fmt.Errorf("base port-forward URL must be non-empty")
	}

	fullPath, err := url.JoinPath(pfq.BaseQueryURL, path)
	if err != nil {
		return nil, fmt.Errorf("joining paths (%s, %s): %s", pfq.BaseQueryURL, path, err)
	}

	req, err := http.NewRequestWithContext(
		ctx,
		"GET",
		fullPath,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create base query request: %s", err)
	}
	q := req.URL.Query()
	for key, val := range params {
		q.Add(key, val)
	}
	req.URL.RawQuery = q.Encode()

	goutil.Logger.Debugf("executing GET to URL %q", req.URL.String())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to GET %s: %s", fullPath, err)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read %s response body: %s", fullPath, err)
	}
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("received non-200 status code %d and data: %s", resp.StatusCode, body)
	}

	return body, nil
}

func (pfq *PortForwardQuerier) QueryPost(
	ctx context.Context,
	path string,
	params map[string]string,
	headers map[string]string,
	body []byte) ([]byte, error) {
	if pfq.BaseQueryURL == "" {
		return nil, fmt.Errorf("base port-forward URL must be non-empty")
	}

	fullPath, err := url.JoinPath(pfq.BaseQueryURL, path)
	if err != nil {
		return nil, fmt.Errorf("joining paths (%s, %s): %s", pfq.BaseQueryURL, path, err)
	}

	req, err := http.NewRequestWithContext(
		ctx,
		"POST",
		fullPath,
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create base query request: %s", err)
	}
	q := req.URL.Query()
	for key, val := range params {
		q.Add(key, val)
	}
	req.URL.RawQuery = q.Encode()

	for k, v := range headers {
		req.Header.Add(k, v)
	}

	log.Printf("executing POST to URL %q", req.URL.String())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to POST %s: %s", fullPath, err)
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read %s response body: %s", fullPath, err)
	}
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("received non-200 status code %d and data: %s", resp.StatusCode, respBody)
	}

	return respBody, nil
}

// reference: https://stackoverflow.com/questions/41545123/how-to-get-pods-under-the-service-with-client-go-the-client-library-of-kubernete
func getServicePods(
	ctx context.Context,
	clientset *kubernetes.Clientset,
	namespace string,
	serviceName string) (*corev1.PodList, error) {
	svc, err := clientset.CoreV1().Services(namespace).Get(ctx, serviceName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get service %s in namespace %s: %s", serviceName, namespace, err)
	}

	labelSet := labels.Set(svc.Spec.Selector)
	labelSelector := labelSet.AsSelector().String()

	pods, err := clientset.CoreV1().
		Pods(namespace).
		List(ctx, metav1.ListOptions{LabelSelector: labelSelector})
	if err != nil {
		return nil, fmt.Errorf("failed to get pods in namespace %s for label selector %s: %s", namespace, labelSelector, err)
	}

	return pods, nil
}
