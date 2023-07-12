package goclient

type Lepton struct {
	HTTP *HTTP
}

func New(remoteURL string, authToken string) *Lepton {
	return &Lepton{
		HTTP: NewHTTP(remoteURL, authToken),
	}
}

func (l *Lepton) Workspace() *Workspace {
	return &Workspace{
		Lepton: *l,
	}
}

func (l *Lepton) Photon() *Photon {
	return &Photon{
		Lepton: *l,
	}
}

func (l *Lepton) Deployment() *Deployment {
	return &Deployment{
		Lepton: *l,
	}
}

func (l *Lepton) Replica() *Replica {
	return &Replica{
		Lepton: *l,
	}
}

func (l *Lepton) Monitoring() *Monitoring {
	return &Monitoring{
		Lepton: *l,
	}
}

func (l *Lepton) Secret() *Secret {
	return &Secret{
		Lepton: *l,
	}
}

func (l *Lepton) Event() *Event {
	return &Event{
		Lepton: *l,
	}
}

func (l *Lepton) Readiness() *Readiness {
	return &Readiness{
		Lepton: *l,
	}
}

func (l *Lepton) Storage() *Storage {
	return &Storage{
		Lepton: *l,
	}
}
