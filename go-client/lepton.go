package goclient

type Lepton struct {
	HTTP *HTTP
}

func New(remoteURL string, authToken string) *Lepton {
	return &Lepton{
		HTTP: NewHTTP(remoteURL, authToken),
	}
}

func (l *Lepton) Cluster() *Cluster {
	return &Cluster{
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

func (l *Lepton) Instance() *Instance {
	return &Instance{
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
