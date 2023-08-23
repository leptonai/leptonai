package controller

import (
	"net/http"

	"github.com/golang/protobuf/ptypes/duration"
	"github.com/golang/protobuf/ptypes/wrappers"
	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"
	"github.com/leptonai/lepton/go-pkg/k8s/ingress"
	"github.com/leptonai/lepton/go-pkg/k8s/service"

	gloogw "github.com/solo-io/gloo/projects/gateway/pkg/api/v1"
	envoycore "github.com/solo-io/gloo/projects/gloo/pkg/api/external/envoy/api/v2/core"
	glooapi "github.com/solo-io/gloo/projects/gloo/pkg/api/v1"
	gloomatchers "github.com/solo-io/gloo/projects/gloo/pkg/api/v1/core/matchers"
	glook8s "github.com/solo-io/gloo/projects/gloo/pkg/api/v1/options/kubernetes"
	gloocore "github.com/solo-io/solo-kit/pkg/api/v1/resources/core"
)

type GlooClients struct {
	gloogw.VirtualServiceClient
	gloogw.RouteTableClient
	glooapi.UpstreamClient
}

const upstreamTimeoutSec = 300
const (
	healthCheckHealthyThreshold   = 2
	healthCheckUnhealthyThreshold = 2
	healthCheckInterval           = 15
	healthCheckTimeout            = 5
)

func getGlooOwnerRefFromLeptonDeployment(ld *leptonaiv1alpha1.LeptonDeployment) *gloocore.Metadata_OwnerReference {
	return &gloocore.Metadata_OwnerReference{
		ApiVersion:         ld.APIVersion,
		Kind:               ld.Kind,
		Name:               ld.Name,
		Uid:                string(ld.UID),
		BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
		Controller:         &wrappers.BoolValue{Value: true},
	}
}

func createRouteTableName(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return ld.Spec.WorkspaceName + "-" + ld.GetSpecName() + "-header-route-table"
}

// Domain label format should match the one in charts/workspace/templates/lb_gloo_route_control_plane.yaml
const RouteTaleDomainLabelKey = "lepton.ai/gloo-route-table-domain"

func createRouteTableDomainLabelValue(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return ld.Spec.WorkspaceName + "-deployments-header-based-routing"
}

func createDeploymentHostname(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return ld.Spec.WorkspaceName + "-" + ld.GetSpecName() + "." + ld.Spec.SharedALBMainDomain
}

func createDeploymentVirtualServiceName(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return ld.Spec.WorkspaceName + "-" + ld.GetSpecName() + "-deployment-virtual-service"
}

func createGlooUpstreamName(ld *leptonaiv1alpha1.LeptonDeployment) string {
	return ld.Spec.WorkspaceName + "-" + ld.GetSpecName() + "-deployment-upstream"
}

func createAuthHeaderValue(token string) string {
	return "Bearer " + token
}

func createNotAuthorizedRoute(ld *leptonaiv1alpha1.LeptonDeployment, addDeploymentHeaderMatcher bool) *gloogw.Route {
	matcher := &gloomatchers.Matcher{
		PathSpecifier: &gloomatchers.Matcher_Prefix{
			Prefix: service.RootPath,
		},
	}
	if addDeploymentHeaderMatcher {
		matcher.Headers = append(matcher.Headers, &gloomatchers.HeaderMatcher{
			Name:  ingress.HTTPHeaderNameForDeployment,
			Value: ld.GetSpecName(),
		})
	}
	route := &gloogw.Route{
		Matchers: []*gloomatchers.Matcher{
			matcher,
		},
		Action: &gloogw.Route_DirectResponseAction{
			DirectResponseAction: &glooapi.DirectResponseAction{
				Status: http.StatusUnauthorized,
				Body:   http.StatusText(http.StatusUnauthorized),
			},
		},
	}
	return route
}

// if maybeToken is nil, it means the route has no requirement on token -- open to all
func createOneRouteForDeployment(ld *leptonaiv1alpha1.LeptonDeployment, maybeToken *string, addDeploymentHeaderMatcher bool) *gloogw.Route {
	headers := make([]*gloomatchers.HeaderMatcher, 0)
	if maybeToken != nil {
		headers = append(headers, &gloomatchers.HeaderMatcher{
			Name:  ingress.HTTPHeaderNameForAuthorization,
			Value: createAuthHeaderValue(*maybeToken),
		})
	}

	if addDeploymentHeaderMatcher {
		headers = append(headers, &gloomatchers.HeaderMatcher{
			Name:  ingress.HTTPHeaderNameForDeployment,
			Value: ld.GetSpecName(),
		})
	}
	return &gloogw.Route{
		Matchers: []*gloomatchers.Matcher{
			{
				PathSpecifier: &gloomatchers.Matcher_Prefix{
					Prefix: service.RootPath,
				},
				Headers: headers,
			},
		},
		Action: &gloogw.Route_RouteAction{
			RouteAction: &glooapi.RouteAction{
				Destination: &glooapi.RouteAction_Single{
					Single: &glooapi.Destination{
						DestinationType: &glooapi.Destination_Upstream{
							Upstream: &gloocore.ResourceRef{
								Name:      createGlooUpstreamName(ld),
								Namespace: ld.Namespace,
							},
						},
					},
				},
			},
		},
		Options: &glooapi.RouteOptions{
			Timeout: &duration.Duration{
				Seconds: upstreamTimeoutSec,
			},
		},
	}
}

// For each token, creating a separate route instead of a separate matcher here, because we want to enforce ratelimiting based on
// token and rate limiting is on route level
func createRoutesBasedOnDeploymentTokens(ld *leptonaiv1alpha1.LeptonDeployment, addDeploymentHeaderMatcher bool) []*gloogw.Route {
	tokens := ld.GetTokens()
	routes := make([]*gloogw.Route, len(tokens))
	if len(tokens) == 0 {
		routes = append(routes, createOneRouteForDeployment(ld, nil, addDeploymentHeaderMatcher))
	} else {
		for i, token := range tokens {
			routes[i] = createOneRouteForDeployment(ld, &token, addDeploymentHeaderMatcher)
		}
		routes = append(routes, createNotAuthorizedRoute(ld, addDeploymentHeaderMatcher))
	}
	return routes
}

func createHeaderBasedDeploymentRouteTable(ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) *gloogw.RouteTable {
	routeTable := gloogw.RouteTable{
		Metadata: &gloocore.Metadata{
			Name:      createRouteTableName(ld),
			Namespace: ld.Namespace,
			Labels: map[string]string{
				RouteTaleDomainLabelKey: createRouteTableDomainLabelValue(ld),
			},
			OwnerReferences: or,
		},
		Routes: createRoutesBasedOnDeploymentTokens(ld, true),
	}
	return &routeTable
}

func createHostBasedDeploymentVirtualService(ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) *gloogw.VirtualService {
	virtualService := gloogw.VirtualService{
		Metadata: &gloocore.Metadata{
			Name:            createDeploymentVirtualServiceName(ld),
			Namespace:       ld.Namespace,
			OwnerReferences: or,
		},
		VirtualHost: &gloogw.VirtualHost{
			Domains: []string{createDeploymentHostname(ld)},
			Routes:  createRoutesBasedOnDeploymentTokens(ld, false),
		},
	}
	return &virtualService
}

func createGlooUpstream(ld *leptonaiv1alpha1.LeptonDeployment, or []*gloocore.Metadata_OwnerReference) *glooapi.Upstream {
	upstream := glooapi.Upstream{
		Metadata: &gloocore.Metadata{
			Name:            createGlooUpstreamName(ld),
			Namespace:       ld.Namespace,
			OwnerReferences: or,
		},
		HealthChecks: []*envoycore.HealthCheck{
			{
				HealthChecker: &envoycore.HealthCheck_HttpHealthCheck_{
					HttpHealthCheck: &envoycore.HealthCheck_HttpHealthCheck{
						Path: service.HealthCheck,
					},
				},
				HealthyThreshold:   &wrappers.UInt32Value{Value: healthCheckHealthyThreshold},
				UnhealthyThreshold: &wrappers.UInt32Value{Value: healthCheckUnhealthyThreshold},
				Interval:           &duration.Duration{Seconds: healthCheckInterval},
				Timeout:            &duration.Duration{Seconds: healthCheckTimeout},
			},
		},

		UpstreamType: &glooapi.Upstream_Kube{
			Kube: &glook8s.UpstreamSpec{
				ServiceName:      service.ServiceName(ld.GetSpecName()),
				ServiceNamespace: ld.Namespace,
				ServicePort:      service.Port,
			},
		},
	}
	return &upstream
}
