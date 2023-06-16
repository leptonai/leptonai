// DomainName is a struct that contains the cell name and root domain.
// It is used to generate the server domain name and deployment name.
// Rules for using this struct:
// 1. CellName must be unique under the same RootDomain
// 2. CellName must match the regular expression [0-9a-z]+
// 3. RootDomain can be any valid domain name and we usually use cloud.lepton.ai
package domainname

import "fmt"

type DomainName struct {
	CellName   string
	RootDomain string
}

func New(cellName, rootDomain string) *DomainName {
	return &DomainName{
		CellName:   cellName,
		RootDomain: rootDomain,
	}
}

func (d *DomainName) GetAPIServer() string {
	if d.RootDomain == "" || d.CellName == "" {
		return ""
	}
	return fmt.Sprintf("%s.%s", d.CellName, d.RootDomain)
}

func (d *DomainName) GetDeployment(deployment string) string {
	if d.RootDomain == "" || d.CellName == "" {
		return ""
	}
	return fmt.Sprintf("%s-%s.%s", d.CellName, deployment, d.RootDomain)
}
