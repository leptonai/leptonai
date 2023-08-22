package httpapi

import (
	"strings"
	"testing"
	"time"

	corev1 "k8s.io/api/core/v1"
	eventsv1 "k8s.io/api/events/v1"
)

func TestGetConditionByType(t *testing.T) {
	conditions := []corev1.PodCondition{
		{
			Type:   corev1.PodScheduled,
			Status: corev1.ConditionTrue,
		},
		{
			Type:   corev1.PodInitialized,
			Status: corev1.ConditionTrue,
		},
		{
			Type:   corev1.PodReady,
			Status: corev1.ConditionTrue,
		},
		{
			Type:   corev1.ContainersReady,
			Status: corev1.ConditionFalse,
		},
		{
			Type:   corev1.DisruptionTarget,
			Status: corev1.ConditionTrue,
		},
	}
	for _, c := range conditions {
		status := getConditionByType(conditions, c.Type).Status
		if status != c.Status {
			t.Errorf("getConditionByType(%v) = %v, want %v", c.Type, status, c.Status)
		}
	}
}

func TestGetEventBy(t *testing.T) {
	events := []eventsv1.Event{
		{
			Type:   "Normal",
			Reason: "Pulling",
			Note:   "Created pod: test",
		},
		{
			Type:   "Warning",
			Reason: "Pulled",
			Note:   "Failed to create pod: test",
		},
	}
	tests := []struct {
		Type        string
		Reason      string
		NotePrefix  string
		ExpectedNil bool
	}{
		{
			Type:        "Normal",
			Reason:      "Pulling",
			NotePrefix:  "Created",
			ExpectedNil: false,
		},
		{
			Type:        "Warning",
			Reason:      "Pulled",
			NotePrefix:  "Failed",
			ExpectedNil: false,
		},
		{
			Type:        "",
			Reason:      "Pulled",
			NotePrefix:  "Failed",
			ExpectedNil: false,
		},
		{
			Type:        "Normal",
			Reason:      "Pulling",
			NotePrefix:  "",
			ExpectedNil: false,
		},
		{
			Type:        "Warning",
			Reason:      "Pulled",
			NotePrefix:  "Created",
			ExpectedNil: true,
		},
	}
	for _, test := range tests {
		e := getLastEvent(events, test.Type, test.Reason, test.NotePrefix)
		if e == nil && !test.ExpectedNil {
			t.Errorf("getLastEventByTypeAndReasonAndNotePrefix(%v, %v, %v) = nil, want non-nil", test.Type, test.Reason, test.NotePrefix)
		}
		if e != nil && test.ExpectedNil {
			t.Errorf("getLastEventByTypeAndReasonAndNotePrefix(%v, %v, %v) != nil, want nil", test.Type, test.Reason, test.NotePrefix)
		}
	}
}

func TestGetReadinessIssueFromEvents(t *testing.T) {
	t.Run("NonExistSecret", testGetReadinessIssueFromEventsNonExistSecret)
	t.Run("PullingImage", testGetReadinessIssueFromEventsPullingImage)
	t.Run("BadImage", testGetReadinessIssueFromEventsBadImage)
	t.Run("BadRegistryToken", testGetReadinessIssueFromEventsBadRegistryToken)
	t.Run("ReadinessProbe", testGetReadinessIssueFromEventsReadinessProbe)
	t.Run("BackOffUnknown", testGetReadinessIssueFromEventsBackOffUnknown)
}

func testGetReadinessIssueFromEventsNonExistSecret(t *testing.T) {
	s := `
Normal   Scheduled  18s   default-scheduler  Successfully assigned ws-ccding/test-548cf57db6-vzdv2 to ip-10-0-47-187.ec2.internal
Normal   Pulling    18s   kubelet            Pulling image "amazon/aws-cli"
Normal   Pulled     18s   kubelet            Successfully pulled image "amazon/aws-cli" in 130.21539ms (130.226829ms including waiting)
Normal   Created    18s   kubelet            Created container env-preparation
Normal   Started    17s   kubelet            Started container env-preparation
Normal   Pulling    15s   kubelet            Pulling image "python:3.10-slim"
Normal   Pulled     14s   kubelet            Successfully pulled image "python:3.10-slim" in 1.153115093s (1.153128104s including waiting)
Warning  Failed     14s   kubelet            Error: couldn't find key non-exist in Secret ws-ccding/lepton-deployment-secret
`
	events := parseStringToEvents(s)
	issue := getReadinessIssueFromEvents(events)
	if issue.Reason != ReadinessReasonConfigError {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Reason, ReadinessReasonConfigError)
	}
	if issue.Message != "Secret not found" {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Message, "Secret not found")
	}
}

func testGetReadinessIssueFromEventsPullingImage(t *testing.T) {
	s := `
Normal   Scheduled  18s   default-scheduler  Successfully assigned ws-ccding/test-548cf57db6-vzdv2 to ip-10-0-47-187.ec2.internal
Normal   Pulling    18s   kubelet            Pulling image "amazon/aws-cli"
Normal   Pulled     18s   kubelet            Successfully pulled image "amazon/aws-cli" in 130.21539ms (130.226829ms including waiting)
Normal   Created    18s   kubelet            Created container env-preparation
Normal   Started    17s   kubelet            Started container env-preparation
Normal   Pulling    15s   kubelet            Pulling image "python:3.10-slim"
`
	events := parseStringToEvents(s)
	issue := getReadinessIssueFromEvents(events)
	if issue.Reason != ReadinessReasonInProgress {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Reason, ReadinessReasonInProgress)
	}
	if issue.Message != "Pulling image" {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Message, "Pulling image")
	}
}

func testGetReadinessIssueFromEventsBadImage(t *testing.T) {
	s := `
Normal   Scheduled  21s               default-scheduler  Successfully assigned ws-ccding/testd-7987cd58b4-x9gk7 to ip-10-0-47-187.ec2.internal
Normal   Pulling    20s               kubelet            Pulling image "amazon/aws-cli"
Normal   Pulled     20s               kubelet            Successfully pulled image "amazon/aws-cli" in 177.681422ms (177.696871ms including waiting)
Normal   Created    20s               kubelet            Created container env-preparation
Normal   Started    20s               kubelet            Started container env-preparation
Normal   Pulling    3s                kubelet            Pulling image "python:3.10-slim-bad"
Warning  Failed     2s                kubelet            Failed to pull image "python:3.10-slim-bad": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/python:3.10-slim-bad": failed to resolve reference "docker.io/library/python:3.10-slim-bad": docker.io/library/python:3.10-slim-bad: not found
Warning  Failed     1s                kubelet            Error: ErrImagePull
`
	events := parseStringToEvents(s)
	issue := getReadinessIssueFromEvents(events)
	if issue.Reason != ReadinessReasonConfigError {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Reason, ReadinessReasonConfigError)
	}
	if issue.Message != "Failed to pull image: not found" {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Message, "Failed to pull image: not found")
	}
}

func testGetReadinessIssueFromEventsBadRegistryToken(t *testing.T) {
	s := `
Normal   Scheduled  27s                default-scheduler  Successfully assigned ws-ccding/bad-registry-58466ff888-kjh8p to ip-10-0-14-170.ec2.internal
Normal   Pulling    13s                kubelet            Pulling image "amazon/aws-cli"
Warning  Failed     13s                kubelet            Failed to pull image "amazon/aws-cli": rpc error: code = Unknown desc = failed to pull and unpack image "docker.io/amazon/aws-cli:latest": failed to resolve reference "docker.io/amazon/aws-cli:latest": failed to authorize: failed to fetch oauth token: unexpected status from GET request to https://auth.docker.io/token?scope=repository%3Aamazon%2Faws-cli%3Apull&service=registry.docker.io: 401 Unauthorized
Warning  Failed     13s                kubelet            Error: ErrImagePull
Normal   BackOff    1s                 kubelet            Back-off pulling image "amazon/aws-cli"
Warning  Failed     1s                 kubelet            Error: ImagePullBackOff
`
	events := parseStringToEvents(s)
	issue := getReadinessIssueFromEvents(events)
	if issue.Reason != ReadinessReasonConfigError {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Reason, ReadinessReasonConfigError)
	}
	if issue.Message != "Failed to pull image due to invalid dockerhub credentials" {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Message, "Failed to pull image due to invalid dockerhub credentials")
	}
}

func testGetReadinessIssueFromEventsReadinessProbe(t *testing.T) {
	s := `
Normal   Scheduled  11s   default-scheduler  Successfully assigned ws-ccding/newgpt2-5567f95f86-5b9m6 to ip-10-0-14-170.ec2.internal
Normal   Pulling    10s   kubelet            Pulling image "amazon/aws-cli"
Normal   Pulled     10s   kubelet            Successfully pulled image "amazon/aws-cli" in 142.711137ms (142.722916ms including waiting)
Normal   Created    10s   kubelet            Created container env-preparation
Normal   Started    10s   kubelet            Started container env-preparation
Normal   Pulling    9s    kubelet            Pulling image "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.8.0-alpha.2"
Normal   Pulled     8s    kubelet            Successfully pulled image "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.8.0-alpha.2" in 134.78012ms (134.80177ms including waiting)
Normal   Created    8s    kubelet            Created container main-container
Normal   Started    8s    kubelet            Started container main-container
Warning  Unhealthy  0s    kubelet            Readiness probe failed: dial tcp 10.0.4.205:8080: connect: connection refused
`
	events := parseStringToEvents(s)
	issue := getReadinessIssueFromEvents(events)
	if issue.Reason != ReadinessReasonInProgress {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Reason, ReadinessReasonInProgress)
	}
	if issue.Message != "Readiness probe failed: dial tcp port 8080: connect: connection refused" {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Message, "Readiness probe failed: dial tcp port 8080: connect: connection refused")
	}
}

func testGetReadinessIssueFromEventsBackOffUnknown(t *testing.T) {
	s := `
Normal   Scheduled  28s               default-scheduler  Successfully assigned ws-ccding/ggg-7744df989d-stm9h to ip-10-0-14-170.ec2.internal
Normal   Pulled     27s               kubelet            Successfully pulled image "amazon/aws-cli" in 158.500996ms (158.512555ms including waiting)
Normal   Pulled     26s               kubelet            Successfully pulled image "amazon/aws-cli" in 120.082473ms (120.094914ms including waiting)
Normal   Pulling    9s                kubelet            Pulling image "amazon/aws-cli"
Normal   Created    9s                kubelet            Created container env-preparation
Normal   Started    9s                kubelet            Started container env-preparation
Normal   Pulled     9s                kubelet            Successfully pulled image "amazon/aws-cli" in 143.790292ms (143.803113ms including waiting)
Warning  BackOff    7s                kubelet            Back-off restarting failed container env-preparation in pod ggg-7744df989d-stm9h_ws-ccding(8361312a-6798-440c-bb48-ecc120156ecd)
`
	events := parseStringToEvents(s)
	issue := getReadinessIssueFromEvents(events)
	if issue.Reason != ReadinessReasonUnknown {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Reason, ReadinessReasonUnknown)
	}
	if issue.Message != "" {
		t.Errorf("getReadinessIssueFromEvents(%v) = %v, want %v", s, issue.Message, "")
	}
}

func parseStringToEvents(s string) []eventsv1.Event {
	lines := strings.Split(s, "\n")
	events := make([]eventsv1.Event, 0)
	for _, line := range lines {
		line = strings.TrimSpace(line)
		event := parseStringToEvent(line)
		if event != nil {
			events = append(events, *event)
		}
	}
	return events
}

func parseStringToEvent(s string) *eventsv1.Event {
	event := eventsv1.Event{}
	fields := strings.Fields(s)
	if len(fields) < 5 {
		return &event
	}
	event.Type = fields[0]
	event.Reason = fields[1]
	event.Note = strings.Join(fields[4:], " ")
	duration, err := time.ParseDuration(fields[2])
	if err != nil {
		duration = 0
	}
	event.EventTime.Time = time.Now().Add(-duration)
	return &event
}
