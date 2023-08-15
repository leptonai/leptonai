package httpapi

import (
	"time"

	eventv1 "k8s.io/api/events/v1"
)

type LeptonDeploymentEvent struct {
	Type   string `json:"type"`
	Reason string `json:"reason"`

	Count            int       `json:"count"`
	LastObservedTime time.Time `json:"last_observed_time"`
}

func convertK8sEventsToLeptonDeploymentEvents(es eventv1.EventList) []LeptonDeploymentEvent {
	leptonEvents := make([]LeptonDeploymentEvent, 0, len(es.Items))

	for _, e := range es.Items {
		leptonEvent := LeptonDeploymentEvent{
			Type:   e.Type,
			Reason: e.Reason,
		}
		leptonEvent.Count = 1
		leptonEvent.LastObservedTime = getEventLastObservedTime(&e)

		if e.Series != nil {
			leptonEvent.Count = int(e.Series.Count)
			if !e.Series.LastObservedTime.Time.IsZero() {
				leptonEvent.LastObservedTime = e.Series.LastObservedTime.Time
			}
		}
		leptonEvents = append(leptonEvents, leptonEvent)
	}

	return leptonEvents
}
