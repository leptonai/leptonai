package v1alpha1

const (
	// General Purpose
	GP1HiddenTest = LeptonDeploymentResourceShape("gp1.hidden_test")
	GP1Small      = LeptonDeploymentResourceShape("gp1.small")
	GP1Medium     = LeptonDeploymentResourceShape("gp1.medium")
	GP1Large      = LeptonDeploymentResourceShape("gp1.large")

	// Accelerated Computing
	AC1T4  = LeptonDeploymentResourceShape("ac1.t4")
	AC1A10 = LeptonDeploymentResourceShape("ac1.a10")
	// Not supported yet
	// AC1A100 = LeptonDeploymentResourceShape("ac1.a100")

	// Other
	Customized = LeptonDeploymentResourceShape("customized")
)

// DisplayShapeToShape converts the display name to a resource shape.
// If the input name is already a resource shape name, also return the corresponding shape.
func DisplayShapeToShape(ds string) LeptonDeploymentResourceShape {
	s, ok := displayNameToShapeName[ds]
	if ok {
		return s
	}
	return LeptonDeploymentResourceShape(ds)
}

var displayNameToShapeName = map[string]LeptonDeploymentResourceShape{
	"cpu.small":  GP1Small,
	"cpu.medium": GP1Medium,
	"cpu.large":  GP1Large,
	"gpu.t4":     AC1T4,
	"gpu.a10":    AC1A10,
}

var SupportedShapesAWS = map[LeptonDeploymentResourceShape]*ResourceShape{
	// General Purpose
	GP1HiddenTest: {
		Name:        "gp1.hidden_test",
		Description: "Hidden test shape with 0.3 CPUs and 128MB of RAM",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:                  0.3,
			Memory:               128,
			EphemeralStorageInGB: 16,
		},
	},
	GP1Small: {
		Name:        "gp1.small",
		Description: "General purpose small shape with 1 CPUs, 4GB of RAM and 16GB of ephemeral storage",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:                  1,
			Memory:               4 * 1024,
			EphemeralStorageInGB: 16,
		},
	},
	GP1Medium: {
		Name:        "gp1.medium",
		Description: "General purpose medium shape with 2 CPUs, 8GB of RAM and 32GB of ephemeral storage",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:                  2,
			Memory:               8 * 1024,
			EphemeralStorageInGB: 32,
		},
	},
	GP1Large: {
		Name:        "gp1.large",
		Description: "General purpose large shape with 4 CPUs, 16GB of RAM and 64GB of ephemeral storage",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:                  4,
			Memory:               16 * 1024,
			EphemeralStorageInGB: 64,
		},
	},

	// Accelerated Computing
	AC1T4: {
		Name:        "ac1.t4",
		Description: "Accelerated computing shape with 1 16GB T4 GPU, 4 CPUs, 16GB of RAM and 100GB of ephemeral storage",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:                  4,
			Memory:               16 * 1024,
			EphemeralStorageInGB: 100,
			AcceleratorType:      "Tesla-T4",
			AcceleratorNum:       1,
		},
	},
	AC1A10: {
		Name:        "ac1.a10",
		Description: "Accelerated computing shape with 1 24GB A10 GPU, 8 CPUs, 32GB of RAM and 400GB of ephemeral storage",
		Resource: LeptonDeploymentReplicaResourceRequirement{
			CPU:                  8,
			Memory:               32 * 1024,
			EphemeralStorageInGB: 400,
			AcceleratorType:      "NVIDIA-A10G",
			AcceleratorNum:       1,
		},
	},
	// Not supported yet
	// AC1A100: {
	// 	Name:        "ac1.a100",
	// 	Description: "Accelerated computing shape with 1 80GB A100 GPU, 12 CPUs, 144GB of RAM and 975GB of ephemeral storage",
	// 	Resource: LeptonDeploymentReplicaResourceRequirement{
	// 		CPU:                  12,
	// 		Memory:               144 * 1024,
	// 		EphemeralStorageInGB: 975,
	// 		AcceleratorType:      "Not supported yet",
	// 		AcceleratorNum:       1,
	// 	},
	// },
}
