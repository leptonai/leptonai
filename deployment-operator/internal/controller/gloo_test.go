package controller

import (
	"net/http"
	"reflect"
	"testing"

	leptonaiv1alpha1 "github.com/leptonai/lepton/deployment-operator/api/v1alpha1"

	"github.com/golang/protobuf/ptypes/duration"
	"github.com/golang/protobuf/ptypes/wrappers"
	gloogw "github.com/solo-io/gloo/projects/gateway/pkg/api/v1"
	envoycore "github.com/solo-io/gloo/projects/gloo/pkg/api/external/envoy/api/v2/core"
	glooapi "github.com/solo-io/gloo/projects/gloo/pkg/api/v1"
	gloomatchers "github.com/solo-io/gloo/projects/gloo/pkg/api/v1/core/matchers"
	glook8s "github.com/solo-io/gloo/projects/gloo/pkg/api/v1/options/kubernetes"
	gloocore "github.com/solo-io/solo-kit/pkg/api/v1/resources/core"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var testLD = createTestLeptonDeployment()

func createTestLeptonDeployment() *leptonaiv1alpha1.LeptonDeployment {
	return &leptonaiv1alpha1.LeptonDeployment{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "ldCRDV1",
			Kind:       "ldCRDKind",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "ldObjectName",
			UID:       "ldObjectUid",
			Namespace: "ldObjectNs",
		},
		Spec: leptonaiv1alpha1.LeptonDeploymentSpec{
			LeptonDeploymentSystemSpec: leptonaiv1alpha1.LeptonDeploymentSystemSpec{
				SharedALBMainDomain: "example.lepton.ai",
				WorkspaceName:       "wsName",
				WorkspaceToken:      "workspaceToken",
			},
			LeptonDeploymentUserSpec: leptonaiv1alpha1.LeptonDeploymentUserSpec{
				Name: "userSpecName",
				APITokens: []leptonaiv1alpha1.TokenVar{
					{
						Value: "tokenName",
					},
					{
						ValueFrom: leptonaiv1alpha1.TokenValue{
							TokenNameRef: leptonaiv1alpha1.TokenNameRefWorkspaceToken,
						},
					},
				},
			},
		},
	}
}

func TestCreateHeaderBasedDeploymentRouteTable(t *testing.T) {
	actual := createHeaderBasedDeploymentRouteTable(testLD, []*gloocore.Metadata_OwnerReference{getGlooOwnerRefFromLeptonDeployment(testLD)})
	exptected := gloogw.RouteTable{
		Metadata: &gloocore.Metadata{
			Name:      "wsName-userSpecName-header-route-table",
			Namespace: "ldObjectNs",
			Labels: map[string]string{
				RouteTaleDomainLabelKey: "wsName-deployments-header-based-routing",
			},
			OwnerReferences: []*gloocore.Metadata_OwnerReference{
				{
					ApiVersion:         "ldCRDV1",
					Kind:               "ldCRDKind",
					Name:               "ldObjectName",
					Uid:                "ldObjectUid",
					BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
					Controller:         &wrappers.BoolValue{Value: true},
				},
			},
		},
		Routes: []*gloogw.Route{
			{
				// route for user specified token
				Matchers: []*gloomatchers.Matcher{
					{
						PathSpecifier: &gloomatchers.Matcher_Prefix{
							Prefix: "/",
						},
						Headers: []*gloomatchers.HeaderMatcher{
							{
								Name:  "Authorization",
								Value: "Bearer tokenName",
							},
							{
								Name:  "X-Lepton-Deployment",
								Value: "userSpecName",
							},
						},
					},
				},
				Action: &gloogw.Route_RouteAction{
					RouteAction: &glooapi.RouteAction{
						Destination: &glooapi.RouteAction_Single{
							Single: &glooapi.Destination{
								DestinationType: &glooapi.Destination_Upstream{
									Upstream: &gloocore.ResourceRef{
										Name:      "wsName-userSpecName-deployment-upstream",
										Namespace: "ldObjectNs",
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
			},
			{
				// route for workspace token
				Matchers: []*gloomatchers.Matcher{
					{
						PathSpecifier: &gloomatchers.Matcher_Prefix{
							Prefix: "/",
						},
						Headers: []*gloomatchers.HeaderMatcher{
							{
								Name:  "Authorization",
								Value: "Bearer workspaceToken",
							},
							{
								Name:  "X-Lepton-Deployment",
								Value: "userSpecName",
							},
						},
					},
				},
				Action: &gloogw.Route_RouteAction{
					RouteAction: &glooapi.RouteAction{
						Destination: &glooapi.RouteAction_Single{
							Single: &glooapi.Destination{
								DestinationType: &glooapi.Destination_Upstream{
									Upstream: &gloocore.ResourceRef{
										Name:      "wsName-userSpecName-deployment-upstream",
										Namespace: "ldObjectNs",
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
			},
			{
				// route for not authorized: any request that reachers here with the deployment header
				Matchers: []*gloomatchers.Matcher{
					{
						PathSpecifier: &gloomatchers.Matcher_Prefix{
							Prefix: "/",
						},
						Headers: []*gloomatchers.HeaderMatcher{
							{
								Name:  "X-Lepton-Deployment",
								Value: "userSpecName",
							},
						},
					},
				},
				Action: &gloogw.Route_DirectResponseAction{
					DirectResponseAction: &glooapi.DirectResponseAction{
						Status: 401,
						Body:   http.StatusText(http.StatusUnauthorized),
					},
				},
			},
		},
	}

	if exptected.String() != actual.String() {
		t.Errorf("Wront output: \n%s \nvs \n%s", exptected.String(), actual.String())
	}
}

func TestCreateHeaderBasedDeploymentRouteTableEmptyToken(t *testing.T) {
	testLDNoToken := createTestLeptonDeployment()
	testLDNoToken.Spec.APITokens = nil
	actual := createHeaderBasedDeploymentRouteTable(testLDNoToken, []*gloocore.Metadata_OwnerReference{getGlooOwnerRefFromLeptonDeployment(testLD)})
	exptected := gloogw.RouteTable{
		Metadata: &gloocore.Metadata{
			Name:      "wsName-userSpecName-header-route-table",
			Namespace: "ldObjectNs",
			Labels: map[string]string{
				RouteTaleDomainLabelKey: "wsName-deployments-header-based-routing",
			},
			OwnerReferences: []*gloocore.Metadata_OwnerReference{
				{
					ApiVersion:         "ldCRDV1",
					Kind:               "ldCRDKind",
					Name:               "ldObjectName",
					Uid:                "ldObjectUid",
					BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
					Controller:         &wrappers.BoolValue{Value: true},
				},
			},
		},
		Routes: []*gloogw.Route{
			{
				// route for user specified token
				Matchers: []*gloomatchers.Matcher{
					{
						PathSpecifier: &gloomatchers.Matcher_Prefix{
							Prefix: "/",
						},
						Headers: []*gloomatchers.HeaderMatcher{
							{
								Name:  "X-Lepton-Deployment",
								Value: "userSpecName",
							},
						},
					},
				},
				Action: &gloogw.Route_RouteAction{
					RouteAction: &glooapi.RouteAction{
						Destination: &glooapi.RouteAction_Single{
							Single: &glooapi.Destination{
								DestinationType: &glooapi.Destination_Upstream{
									Upstream: &gloocore.ResourceRef{
										Name:      "wsName-userSpecName-deployment-upstream",
										Namespace: "ldObjectNs",
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
			},
		},
	}

	if exptected.String() != actual.String() {
		t.Errorf("Wront output: \n%s \nvs \n%s", exptected.String(), actual.String())
	}
}

func TestCreateDomainBasedDeploymentVirtualServiceEmptyToken(t *testing.T) {
	testLDNoToken := createTestLeptonDeployment()
	testLDNoToken.Spec.APITokens = nil
	actual := createHostBasedDeploymentVirtualService(testLDNoToken, []*gloocore.Metadata_OwnerReference{getGlooOwnerRefFromLeptonDeployment(testLD)})
	exptected := gloogw.VirtualService{
		Metadata: &gloocore.Metadata{
			Name:      "wsName-userSpecName-deployment-virtual-service",
			Namespace: "ldObjectNs",
			OwnerReferences: []*gloocore.Metadata_OwnerReference{
				{
					ApiVersion:         "ldCRDV1",
					Kind:               "ldCRDKind",
					Name:               "ldObjectName",
					Uid:                "ldObjectUid",
					BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
					Controller:         &wrappers.BoolValue{Value: true},
				},
			},
		},
		VirtualHost: &gloogw.VirtualHost{
			Domains: []string{
				"wsName-userSpecName.example.lepton.ai",
			},
			Routes: []*gloogw.Route{
				{
					// route for user specified token
					Matchers: []*gloomatchers.Matcher{
						{
							PathSpecifier: &gloomatchers.Matcher_Prefix{
								Prefix: "/",
							},
						},
					},
					Action: &gloogw.Route_RouteAction{
						RouteAction: &glooapi.RouteAction{
							Destination: &glooapi.RouteAction_Single{
								Single: &glooapi.Destination{
									DestinationType: &glooapi.Destination_Upstream{
										Upstream: &gloocore.ResourceRef{
											Name:      "wsName-userSpecName-deployment-upstream",
											Namespace: "ldObjectNs",
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
				},
			},
		},
	}

	if exptected.String() != actual.String() {
		t.Errorf("Wront output: \n%s \nvs \n%s", exptected.String(), actual.String())
	}
}

func TestCreateDomainBasedDeploymentVirtualService(t *testing.T) {
	actual := createHostBasedDeploymentVirtualService(testLD, []*gloocore.Metadata_OwnerReference{getGlooOwnerRefFromLeptonDeployment(testLD)})
	exptected := gloogw.VirtualService{
		Metadata: &gloocore.Metadata{
			Name:      "wsName-userSpecName-deployment-virtual-service",
			Namespace: "ldObjectNs",
			OwnerReferences: []*gloocore.Metadata_OwnerReference{
				{
					ApiVersion:         "ldCRDV1",
					Kind:               "ldCRDKind",
					Name:               "ldObjectName",
					Uid:                "ldObjectUid",
					BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
					Controller:         &wrappers.BoolValue{Value: true},
				},
			},
		},
		VirtualHost: &gloogw.VirtualHost{
			Domains: []string{
				"wsName-userSpecName.example.lepton.ai",
			},
			Routes: []*gloogw.Route{
				{
					// route for user specified token
					Matchers: []*gloomatchers.Matcher{
						{
							PathSpecifier: &gloomatchers.Matcher_Prefix{
								Prefix: "/",
							},
							Headers: []*gloomatchers.HeaderMatcher{
								{
									Name:  "Authorization",
									Value: "Bearer tokenName",
								},
							},
						},
					},
					Action: &gloogw.Route_RouteAction{
						RouteAction: &glooapi.RouteAction{
							Destination: &glooapi.RouteAction_Single{
								Single: &glooapi.Destination{
									DestinationType: &glooapi.Destination_Upstream{
										Upstream: &gloocore.ResourceRef{
											Name:      "wsName-userSpecName-deployment-upstream",
											Namespace: "ldObjectNs",
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
				},
				{
					// route for workspace token
					Matchers: []*gloomatchers.Matcher{
						{
							PathSpecifier: &gloomatchers.Matcher_Prefix{
								Prefix: "/",
							},
							Headers: []*gloomatchers.HeaderMatcher{
								{
									Name:  "Authorization",
									Value: "Bearer workspaceToken",
								},
							},
						},
					},
					Action: &gloogw.Route_RouteAction{
						RouteAction: &glooapi.RouteAction{
							Destination: &glooapi.RouteAction_Single{
								Single: &glooapi.Destination{
									DestinationType: &glooapi.Destination_Upstream{
										Upstream: &gloocore.ResourceRef{
											Name:      "wsName-userSpecName-deployment-upstream",
											Namespace: "ldObjectNs",
										},
									},
								},
							},
						},
					},
					Options: &glooapi.RouteOptions{
						Timeout: &duration.Duration{
							Seconds: 300,
						},
					},
				},
				{
					// route for not authorized
					Matchers: []*gloomatchers.Matcher{
						{
							PathSpecifier: &gloomatchers.Matcher_Prefix{
								Prefix: "/",
							},
						},
					},
					Action: &gloogw.Route_DirectResponseAction{
						DirectResponseAction: &glooapi.DirectResponseAction{
							Status: 401,
							Body:   http.StatusText(http.StatusUnauthorized),
						},
					},
				},
			},
		},
	}

	if exptected.String() != actual.String() {
		t.Errorf("Wront output: \n%s \nvs \n%s", exptected.String(), actual.String())
	}
}

func TestCreateGlooUpstream(t *testing.T) {
	actual := createGlooUpstream(testLD, []*gloocore.Metadata_OwnerReference{getGlooOwnerRefFromLeptonDeployment(testLD)})
	exptected := glooapi.Upstream{
		Metadata: &gloocore.Metadata{
			Name:      "wsName-userSpecName-deployment-upstream",
			Namespace: "ldObjectNs",
			OwnerReferences: []*gloocore.Metadata_OwnerReference{
				{
					ApiVersion:         "ldCRDV1",
					Kind:               "ldCRDKind",
					Name:               "ldObjectName",
					Uid:                "ldObjectUid",
					BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
					Controller:         &wrappers.BoolValue{Value: true},
				},
			},
		},
		HealthChecks: []*envoycore.HealthCheck{
			{
				HealthChecker: &envoycore.HealthCheck_HttpHealthCheck_{
					HttpHealthCheck: &envoycore.HealthCheck_HttpHealthCheck{
						Path: "/healthz",
					},
				},
				HealthyThreshold:   &wrappers.UInt32Value{Value: 2},
				UnhealthyThreshold: &wrappers.UInt32Value{Value: 2},
				Interval:           &duration.Duration{Seconds: 15},
				Timeout:            &duration.Duration{Seconds: 5},
			},
		},

		UpstreamType: &glooapi.Upstream_Kube{
			Kube: &glook8s.UpstreamSpec{
				ServiceName:      "userSpecName-service",
				ServiceNamespace: "ldObjectNs",
				ServicePort:      8080,
			},
		},
	}

	if exptected.String() != actual.String() {
		t.Errorf("Wront output: \n%s \nvs \n%s", exptected.String(), actual.String())
	}
}

func TestCompareAndPatchGlooMetadata(t *testing.T) {
	tests := []struct {
		meta         *gloocore.Metadata
		patch        *gloocore.Metadata
		expected     bool
		expectedMeta *gloocore.Metadata
	}{
		{
			meta: &gloocore.Metadata{
				Labels: map[string]string{
					"key1": "value1",
				},
				Annotations: map[string]string{
					"ann1": "annValue1",
				},
				OwnerReferences: []*gloocore.Metadata_OwnerReference{
					{
						ApiVersion:         "ldCRDV1",
						Kind:               "ldCRDKind",
						Name:               "ldObjectName",
						Uid:                "ldObjectUid",
						BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
						Controller:         &wrappers.BoolValue{Value: true},
					},
				},
			},
			patch: &gloocore.Metadata{
				Labels: map[string]string{
					"key1": "value1",
				},
				Annotations: map[string]string{
					"ann1": "annValue1",
				},
				OwnerReferences: []*gloocore.Metadata_OwnerReference{
					{
						ApiVersion:         "ldCRDV1",
						Kind:               "ldCRDKind",
						Name:               "ldObjectName",
						Uid:                "ldObjectUid",
						BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
						Controller:         &wrappers.BoolValue{Value: true},
					},
				},
			},
			expected: true,
			expectedMeta: &gloocore.Metadata{
				Labels: map[string]string{
					"key1": "value1",
				},
				Annotations: map[string]string{
					"ann1": "annValue1",
				},
				OwnerReferences: []*gloocore.Metadata_OwnerReference{
					{
						ApiVersion:         "ldCRDV1",
						Kind:               "ldCRDKind",
						Name:               "ldObjectName",
						Uid:                "ldObjectUid",
						BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
						Controller:         &wrappers.BoolValue{Value: true},
					},
				},
			},
		},
		{
			meta: &gloocore.Metadata{
				Labels: map[string]string{
					"key1": "value1",
				},
				Annotations: map[string]string{
					"ann1": "annValue1",
				},
				OwnerReferences: []*gloocore.Metadata_OwnerReference{
					{
						ApiVersion:         "ldCRDV1",
						Kind:               "ldCRDKind",
						Name:               "ldObjectName",
						Uid:                "ldObjectUid",
						BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
						Controller:         &wrappers.BoolValue{Value: true},
					},
				},
			},
			patch: &gloocore.Metadata{
				Labels: map[string]string{
					"key2": "value2",
				},
				Annotations: map[string]string{
					"ann1": "annValue2",
				},
				OwnerReferences: []*gloocore.Metadata_OwnerReference{
					{
						ApiVersion:         "ldCRDV2",
						Kind:               "ldCRDKind",
						Name:               "ldObjectName",
						Uid:                "ldObjectUid",
						BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
						Controller:         &wrappers.BoolValue{Value: true},
					},
				},
			},
			expected: false,
			expectedMeta: &gloocore.Metadata{
				Labels: map[string]string{
					"key1": "value1",
					"key2": "value2",
				},
				Annotations: map[string]string{
					"ann1": "annValue2",
				},
				OwnerReferences: []*gloocore.Metadata_OwnerReference{
					{
						ApiVersion:         "ldCRDV2",
						Kind:               "ldCRDKind",
						Name:               "ldObjectName",
						Uid:                "ldObjectUid",
						BlockOwnerDeletion: &wrappers.BoolValue{Value: true},
						Controller:         &wrappers.BoolValue{Value: true},
					},
				},
			},
		},
	}

	for _, test := range tests {
		equals := compareAndPatchGlooMetadata(test.meta, test.patch)
		if equals != test.expected {
			t.Errorf("Wrong output: %v vs %v", equals, test.expected)
		}
		if !reflect.DeepEqual(test.meta, test.expectedMeta) {
			t.Errorf("Wrong output: \n%s \nvs \n%s", test.meta.String(), test.expectedMeta.String())
		}
	}
}
