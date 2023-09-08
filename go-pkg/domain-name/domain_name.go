// DomainName is a struct that contains the workspace name and root domain.
// It is used to generate the server domain name and deployment name.
// Rules for using this struct:
// 1. WorkspaceName must be unique under the same RootDomain
// 2. WorkspaceName must match the regular expression [0-9a-z]+
// 3. RootDomain can be any valid domain name and we usually use cloud.lepton.ai
package domainname

import "fmt"

type DomainName struct {
	WorkspaceName string
	RootDomain    string
}

func New(workspaceName, rootDomain string) *DomainName {
	return &DomainName{
		WorkspaceName: workspaceName,
		RootDomain:    rootDomain,
	}
}

func (d *DomainName) GetAPIServer() string {
	if d.RootDomain == "" || d.WorkspaceName == "" {
		return ""
	}
	return fmt.Sprintf("%s.%s", d.WorkspaceName, d.RootDomain)
}

func (d *DomainName) GetDeployment(deployment string) string {
	if d.RootDomain == "" || d.WorkspaceName == "" {
		return ""
	}
	return fmt.Sprintf("%s-%s.%s", d.WorkspaceName, deployment, d.RootDomain)
}
