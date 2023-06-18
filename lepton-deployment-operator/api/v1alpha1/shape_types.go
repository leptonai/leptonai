package v1alpha1

const (
	GP1HiddenTest = LeptonDeploymentResourceShape("gp1.hidden_test")
	GP1Small      = LeptonDeploymentResourceShape("gp1.small")
	GP1Medium     = LeptonDeploymentResourceShape("gp1.medium")
	GP1Large      = LeptonDeploymentResourceShape("gp1.large")
)

var SupportedShapesAWS = map[LeptonDeploymentResourceShape]*ResourceShape{
	GP1HiddenTest: {
		Name:        "gp1.hidden_test",
		Description: "Hidden test shape with 0.3 CPUs and 128MB of RAM",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:    0.3,
			Memory: 128,
		},
	},
	GP1Small: {
		Name:        "gp1.small",
		Description: "Small shape with 2 CPUs and 8GB of RAM",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:    2,
			Memory: 8 * 1024,
		},
	},
	GP1Medium: {
		Name:        "gp1.medium",
		Description: "Medium shape with 4 CPUs and 16GB of RAM",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:    4,
			Memory: 16 * 1024,
		},
	},
	GP1Large: {
		Name:        "gp1.large",
		Description: "Large shape with 8 CPUs and 32GB of RAM",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:    8,
			Memory: 32 * 1024,
		},
	},
}
