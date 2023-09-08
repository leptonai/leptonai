# https://github.com/kubernetes/autoscaler/issues/3216
# https://github.com/kubernetes/autoscaler/pull/4701
# https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md#iam-policy
resource "aws_iam_policy" "cluster_autoscaler" {
  name        = "${var.cluster_name}-cluster-autoscaler-policy"
  description = "Cluster autoscaler IAM Policy"

  # make sure the cluster-autoscaler only has access
  # to this specific cluster
  # ref. https://aws.github.io/aws-eks-best-practices/cluster-autoscaling/#employ-least-privileged-access-to-the-iam-role
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup",
        ],
        "Resource" : [
          "*"
        ],
        "Condition" : {
          "StringEquals" : {
            "aws:ResourceTag/autoscaler-kind" : "cluster-autoscaler",
            "aws:ResourceTag/k8s.io/cluster-autoscaler/enabled" : "true",
            "aws:ResourceTag/k8s.io/cluster-autoscaler/${local.cluster_name}" : "owned"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeScalingActivities",
          "autoscaling:DescribeTags",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeLaunchTemplateVersions",
          "ec2:DescribeImages",
          "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup"
        ],
        "Resource" : [
          "*"
        ]
      }
    ]
  })

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role" "cluster_autoscaler" {
  name = "${var.cluster_name}-cluster-autoscaler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Federated : "arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
        }
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com",
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:kube-system:cluster-autoscaler-sa"
          }
        }
      },
    ]
  })

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role_policy_attachment" "cluster_autoscaler" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.cluster_autoscaler.name}"
  role       = aws_iam_role.cluster_autoscaler.name

  depends_on = [
    aws_iam_policy.cluster_autoscaler,
    aws_iam_role.cluster_autoscaler
  ]
}

resource "kubernetes_service_account" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscaler-sa"
    namespace = "kube-system"

    labels = {
      "app.kubernetes.io/instance" = "cluster-autoscaler"
      "app.kubernetes.io/name"     = "aws-cluster-autoscaler"
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.cluster_autoscaler.name}"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_autoscaler,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth
  ]
}

# ref. https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
resource "kubernetes_role" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscale-role"
    namespace = "kube-system"
  }

  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["create", "list", "watch"]
  }

  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["cluster-autoscaler-status", "cluster-autoscaler-priority-expander"]
    verbs          = ["delete", "get", "update", "watch"]
  }
}

resource "kubernetes_role_binding" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscale-role-binding"
    namespace = "kube-system"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.cluster_autoscaler.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.cluster_autoscaler.metadata[0].name
    namespace = "kube-system"
  }

  depends_on = [
    kubernetes_service_account.cluster_autoscaler,
    kubernetes_role.cluster_autoscaler,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth
  ]
}

# https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
resource "kubernetes_cluster_role" "cluster_autoscaler" {
  metadata {
    name = "cluster-autoscaler-cluster-role"
  }

  rule {
    api_groups = [""]
    resources  = ["events", "endpoints"]
    verbs      = ["create", "patch"]
  }

  rule {
    api_groups = [""]
    resources  = ["pods/eviction"]
    verbs      = ["create"]
  }

  rule {
    api_groups = [""]
    resources  = ["pods/status"]
    verbs      = ["update"]
  }

  rule {
    api_groups     = [""]
    resources      = ["endpoints"]
    resource_names = ["cluster-autoscaler"]
    verbs          = ["get", "update"]
  }

  rule {
    api_groups = [""]
    resources  = ["nodes"]
    verbs      = ["watch", "list", "get", "update"]
  }

  rule {
    api_groups = [""]
    resources  = ["namespaces", "pods", "services", "replicationcontrollers", "persistentvolumeclaims", "persistentvolumes"]
    verbs      = ["watch", "list", "get"]
  }

  rule {
    api_groups = ["extensions"]
    resources  = ["replicasets", "daemonsets"]
    verbs      = ["watch", "list", "get"]
  }

  rule {
    api_groups = ["policy"]
    resources  = ["poddisruptionbudgets"]
    verbs      = ["watch", "list"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["statefulsets", "replicasets", "daemonsets"]
    verbs      = ["watch", "list", "get"]
  }

  rule {
    api_groups = ["storage.k8s.io"]
    resources  = ["storageclasses", "csinodes", "csidrivers", "csistoragecapacities"]
    verbs      = ["watch", "list", "get"]
  }

  rule {
    api_groups = ["batch", "extensions"]
    resources  = ["jobs"]
    verbs      = ["get", "list", "watch", "patch"]
  }

  rule {
    api_groups = ["coordination.k8s.io"]
    resources  = ["leases"]
    verbs      = ["create"]
  }

  rule {
    api_groups     = ["coordination.k8s.io"]
    resource_names = ["cluster-autoscaler"]
    resources      = ["leases"]
    verbs          = ["get", "update"]
  }

  depends_on = [
    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth
  ]
}

resource "kubernetes_cluster_role_binding" "cluster_autoscaler" {
  metadata {
    name = "cluster-autoscaler-cluster-role-binding"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.cluster_autoscaler.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.cluster_autoscaler.metadata[0].name
    namespace = "kube-system"
  }

  depends_on = [
    kubernetes_service_account.cluster_autoscaler,
    kubernetes_cluster_role.cluster_autoscaler,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth
  ]
}

resource "helm_release" "cluster_autoscaler" {
  name      = "cluster-autoscaler"
  namespace = "kube-system"

  chart      = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"

  # https://github.com/kubernetes/autoscaler/blob/master/charts/cluster-autoscaler/Chart.yaml
  # https://github.com/kubernetes/autoscaler/releases
  version = "9.29.1"

  # https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md
  # https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/main.go
  # https://github.com/kubernetes/autoscaler/blob/master/charts/cluster-autoscaler/values.yaml
  # https://github.com/kubernetes/autoscaler/blob/master/charts/cluster-autoscaler/templates/deployment.yaml
  values = [yamlencode({
    # https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md#auto-discovery-setup
    autoDiscovery = {
      clusterName = var.cluster_name
      tags        = "autoscaler-kind=cluster-autoscaler,k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/${var.cluster_name}=owned"
    }

    awsRegion     = var.region
    cloudProvider = "aws"

    replicaCount = "1"

    # https://github.com/kubernetes/autoscaler/releases
    image = {
      repository = "registry.k8s.io/autoscaling/cluster-autoscaler"
      tag        = "v1.27.2"
    }

    extraArgs = {
      # "Detect similar node groups and balance the number of nodes between them"
      # Default "false"
      balance-similar-node-groups = true

      expander = "least-waste"

      # "If true cluster autoscaler will never delete nodes with pods from kube-system (except for DaemonSet or mirror pods)"
      skip-nodes-with-system-pods = false
      # "If true cluster autoscaler will never delete nodes with pods with local storage, e.g. EmptyDir or HostPath"
      skip-nodes-with-local-storage = false
      # "If true cluster autoscaler will never delete nodes with pods owned by custom controllers"
      # ONLY IN LATEST RELEASE
      skip-nodes-with-custom-controller-pods = false

      # "How long after scale up that scale down evaluation resumes"
      # Default "10m"
      scale-down-delay-after-add = "7m"

      # "How long after scale down failure that scale down evaluation resumes"
      # Default "3m"
      scale-down-delay-after-failure = "3m"

      # "How long a node should be unneeded before it is eligible for scale down"
      # Default "10m"
      scale-down-unneeded-time = "7m"

      # "How long an unready node should be unneeded before it is eligible for scale down"
      # Default "20m"
      scale-down-unready-time = "10m"

      # "Should CA scale down the cluster"
      # Default "true"
      scale-down-enabled = "true"

      # "Should CA scale down unready nodes of the cluster"
      # Default "true"
      # ONLY IN LATEST RELEASE
      scale-down-unready-enabled = "true"

      # "Sum of cpu or memory of all pods running on the node divided by node's corresponding allocatable resource, below which a node can be considered for scale down"
      # Default "0.5"
      scale-down-utilization-threshold = 0.5

      # "Sum of gpu requests of all pods running on the node divided by node's allocatable resource, below which a node can be considered for scale down."
      # "Utilization calculation only cares about gpu resource for accelerator node. cpu and memory utilization will be ignored."
      # Default "0.5"
      scale-down-gpu-utilization-threshold = 0.5

      # "How often cluster is reevaluated for scale up or down"
      # Default "10s"
      scan-interval = "8s"

      # Maximum number of nodes that can be tainted/untainted PreferNoSchedule at the same time.
      # Unneeded nodes are tainted with PreferNoSchedule during scale down.
      # But, possibly taint the new node in "scale-down-delay-after-add" period,
      # while the old node is still being drained/terminated.
      # Can be problematic if the new node is tainted and the old node is not yet drained.
      # Can be problematic if the EKS node group drain operation is slow.
      # Default 10.
      #
      # USE WITH CAUTION
      # Set to 0 to turn off such tainting.
      # Could be helpful to schedule new pods right after AMI rollouts.
      max-bulk-soft-taint-count = 10
    }

    rbac = {
      create = false
      serviceAccount = {
        annotations = {
          "eks.amazonaws.com/role-arn" = aws_iam_role.cluster_autoscaler.arn
        },
        create = false
        name   = "cluster-autoscaler-sa"
      }
    }
  })]

  depends_on = [
    module.eks,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    kubernetes_service_account.cluster_autoscaler,
    kubernetes_role_binding.cluster_autoscaler,
    kubernetes_cluster_role_binding.cluster_autoscaler,

    aws_autoscaling_group_tag.ubuntu_x86_64_cpu_m6a16xlarge_autoscaler_kind,
  ]
}
