package goclient

type Lepton struct {
	HTTP *HTTP
}

func New(remoteURL string) *Lepton {
	return &Lepton{
		HTTP: NewHTTP(remoteURL),
	}
}

func (l *Lepton) Cluster() *Cluster {
	return &Cluster{
		HTTP: l.HTTP,
	}
}

func (l *Lepton) Photon() *Photon {
	return &Photon{
		HTTP: l.HTTP,
	}
}

func (l *Lepton) Deployment() *Deployment {
	return &Deployment{
		HTTP: l.HTTP,
	}
}

func (l *Lepton) Instance() *Instance {
	return &Instance{
		HTTP: l.HTTP,
	}
}

func (l *Lepton) Monitoring() *Monitoring {
	return &Monitoring{
		HTTP: l.HTTP,
	}
}
