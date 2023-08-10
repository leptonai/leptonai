#!/usr/bin/env bash
# CLOUD_IMG: This file was created/modified by the Cloud Image build process
#
# This file is part of the Ubuntu EKS image. This is a customized version of the
# Amazon bootstrap script for the use with Ubuntu EKS images.
#
# Copyright (C) 2020 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3, as published by the
# Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranties of MERCHANTABILITY,
# SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#

set -o pipefail
set -o nounset
set -o errexit

err_report() {
    echo "Exited with error on line $1"
}
trap 'err_report $LINENO' ERR

IFS=$'\n\t'

function print_help {
    echo "usage: $0 [options] <cluster-name>"
    echo "Bootstraps an instance into an EKS cluster"
    echo ""
    echo "-h,--help print this help"
    echo "--use-max-pods Sets --max-pods for the kubelet when true. (default: true)"
    echo "--b64-cluster-ca The base64 encoded cluster CA content. Only valid when used with --apiserver-endpoint. Bypasses calling \"aws eks describe-cluster\""
    echo "--apiserver-endpoint The EKS cluster API Server endpoint. Only valid when used with --b64-cluster-ca. Bypasses calling \"aws eks describe-cluster\""
    echo "--kubelet-extra-args Extra arguments to add to the kubelet. Useful for adding labels or taints."
    echo "--enable-docker-bridge Restores the docker default bridge network. (default: false)"
    echo "--aws-api-retry-attempts Number of retry attempts for AWS API call (DescribeCluster) (default: 3)"
    echo "--docker-config-json The contents of the /etc/docker/daemon.json file. Useful if you want a custom config differing from the default one in the AMI"
    echo "--dns-cluster-ip Overrides the IP address to use for DNS queries within the cluster. Defaults to 10.100.0.10 or 172.20.0.10 based on the IP address of the primary interface"
    echo "--pause-container-account The AWS account (number) to pull the pause container from"
    echo "--pause-container-version The tag of the pause container"
    echo "--container-runtime Specify a container runtime (default: containerd)"
    echo "--ip-family Specify ip family of the cluster"
    echo "--service-ipv6-cidr ipv6 cidr range of the cluster"
}

POSITIONAL=()

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            print_help
            exit 1
            ;;
        --use-max-pods)
            USE_MAX_PODS="$2"
            shift
            shift
            ;;
        --b64-cluster-ca)
            B64_CLUSTER_CA=$2
            shift
            shift
            ;;
        --apiserver-endpoint)
            APISERVER_ENDPOINT=$2
            shift
            shift
            ;;
        --kubelet-extra-args)
            KUBELET_EXTRA_ARGS=$2
            shift
            shift
            ;;
        --enable-docker-bridge)
            ENABLE_DOCKER_BRIDGE=$2
            shift
            shift
            ;;
        --aws-api-retry-attempts)
            API_RETRY_ATTEMPTS=$2
            shift
            shift
            ;;
        --docker-config-json)
            DOCKER_CONFIG_JSON=$2
            shift
            shift
            ;;
        --pause-container-account)
            PAUSE_CONTAINER_ACCOUNT=$2
            shift
            shift
            ;;
        --pause-container-version)
            PAUSE_CONTAINER_VERSION=$2
            shift
            shift
            ;;
        --dns-cluster-ip)
            DNS_CLUSTER_IP=$2
            shift
            shift
            ;;
        --container-runtime)
            CONTAINER_RUNTIME=$2
            shift
            shift
            ;;
        --ip-family)
            IP_FAMILY=$2
            shift
            shift
            ;;
        --service-ipv6-cidr)
            SERVICE_IPV6_CIDR=$2
            shift
            shift
            ;;
        *)    # unknown option
            POSITIONAL+=("$1") # save it in an array for later
            shift # past argument
            ;;
    esac
done

set +u
set -- "${POSITIONAL[@]}" # restore positional parameters
CLUSTER_NAME="$1"
set -u

USE_MAX_PODS="${USE_MAX_PODS:-true}"
B64_CLUSTER_CA="${B64_CLUSTER_CA:-}"
APISERVER_ENDPOINT="${APISERVER_ENDPOINT:-}"
SERVICE_IPV4_CIDR="${SERVICE_IPV4_CIDR:-}"
DNS_CLUSTER_IP="${DNS_CLUSTER_IP:-}"
KUBELET_EXTRA_ARGS="${KUBELET_EXTRA_ARGS:-}"
ENABLE_DOCKER_BRIDGE="${ENABLE_DOCKER_BRIDGE:-false}"
API_RETRY_ATTEMPTS="${API_RETRY_ATTEMPTS:-3}"
DOCKER_CONFIG_JSON="${DOCKER_CONFIG_JSON:-}"
PAUSE_CONTAINER_VERSION="${PAUSE_CONTAINER_VERSION:-3.5}"
DEFAULT_CONTAINER_RUNTIME="containerd"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-$DEFAULT_CONTAINER_RUNTIME}"
# from >= 1.27, the cloud-provider will be external
CLOUD_PROVIDER="aws"
IP_FAMILY="${IP_FAMILY:-}"
SERVICE_IPV6_CIDR="${SERVICE_IPV6_CIDR:-}"

echo "Using $CONTAINER_RUNTIME as the container runtime"

# Helper function which calculates the amount of the given resource (either CPU or memory)
# to reserve in a given resource range, specified by a start and end of the range and a percentage
# of the resource to reserve. Note that we return zero if the start of the resource range is
# greater than the total resource capacity on the node. Additionally, if the end range exceeds the total
# resource capacity of the node, we use the total resource capacity as the end of the range.
# Args:
#   $1 total available resource on the worker node in input unit (either millicores for CPU or Mi for memory)
#   $2 start of the resource range in input unit
#   $3 end of the resource range in input unit
#   $4 percentage of range to reserve in percent*100 (to allow for two decimal digits)
# Return:
#   amount of resource to reserve in input unit
get_resource_to_reserve_in_range() {
  local total_resource_on_instance=$1
  local start_range=$2
  local end_range=$3
  local percentage=$4
  resources_to_reserve="0"
  if (( $total_resource_on_instance > $start_range )); then
    resources_to_reserve=$(((($total_resource_on_instance < $end_range ? \
        $total_resource_on_instance : $end_range) - $start_range) * $percentage / 100 / 100))
  fi
  echo $resources_to_reserve
}

# Calculates the amount of memory to reserve for kubeReserved in mebibytes. KubeReserved is a function of pod
# density so we are calculating the amount of memory to reserve for Kubernetes systems daemons by
# considering the maximum number of pods this instance type supports.
# Args:
#   $1 the max number of pods per instance type (MAX_PODS) based on values from /etc/eks/eni-max-pods.txt
# Return:
#   memory to reserve in Mi for the kubelet
get_memory_mebibytes_to_reserve() {
  local max_num_pods=$1
  memory_to_reserve=$((11 * $max_num_pods + 255))
  echo $memory_to_reserve
}

# Calculates the amount of CPU to reserve for kubeReserved in millicores from the total number of vCPUs available on the instance.
# From the total core capacity of this worker node, we calculate the CPU resources to reserve by reserving a percentage
# of the available cores in each range up to the total number of cores available on the instance.
# We are using these CPU ranges from GKE (https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture#node_allocatable):
# 6% of the first core
# 1% of the next core (up to 2 cores)
# 0.5% of the next 2 cores (up to 4 cores)
# 0.25% of any cores above 4 cores
# Return:
#   CPU resources to reserve in millicores (m)
get_cpu_millicores_to_reserve() {
  local total_cpu_on_instance=$(($(nproc) * 1000))
  local cpu_ranges=(0 1000 2000 4000 $total_cpu_on_instance)
  local cpu_percentage_reserved_for_ranges=(600 100 50 25)
  cpu_to_reserve="0"
  for i in ${!cpu_percentage_reserved_for_ranges[@]}; do
    local start_range=${cpu_ranges[$i]}
    local end_range=${cpu_ranges[(($i+1))]}
    local percentage_to_reserve_for_range=${cpu_percentage_reserved_for_ranges[$i]}
    cpu_to_reserve=$(($cpu_to_reserve + \
        $(get_resource_to_reserve_in_range $total_cpu_on_instance $start_range $end_range $percentage_to_reserve_for_range)))
  done
  echo $cpu_to_reserve
}

_kubelet_snap_options=()

# Call this function instead of "snap set" to configure the kubelet-eks snap.
# This functions mitigates a race condition where there's a snap refresh in the
# background and the set command fails with
#   error: snap "kubelet-eks" has "auto-refresh" change in progress
# resulting in startup of misconfigured kubelet.
kubelet_snap_add_options() {
    _kubelet_snap_options+=("$@")
}

# Call this function before starting the kubelet-eks snap. This function first
# tries to make sure that no refresh is running and then runs "snap set" with
# all options added with the kubelet_snap_add_options function and retries
# several times in case there's a change in progress.
kubelet_snap_configure() {
    local retry ret

    # Wait for a possible running refresh to finish.
    snap watch --last=refresh\?
    snap watch --last=auto-refresh\?

    # If another refresh is running at this point, the snap commands below may
    # fail. But the likelihood of this happening is small.

    # If this succeeds the likelihood of another refresh is even smaller.
    # Ignore the "... no updates available" message.
    snap refresh kubelet-eks 2> >(grep -v ' has no updates available$' >&2) || true

    # Try to set the options every 2 seconds until we succeed or give up after
    # 16 seconds. A possible running refresh shouldn't take longer.
    for (( retry=0; retry < 8; retry++ )); do
        if (( retry )); then
            sleep 2
        fi
        ret=0
        if snap set kubelet-eks "${_kubelet_snap_options[@]}"; then
            break
        else
            ret=$?
        fi
    done

    return $ret
}

if [ -z "$CLUSTER_NAME" ]; then
    echo "CLUSTER_NAME is not defined"
    exit  1
fi

if [[ ! -z "${IP_FAMILY}" ]]; then
  if [[ "${IP_FAMILY}" != "ipv4" ]] && [[ "${IP_FAMILY}" != "ipv6" ]] ; then
        echo "Invalid IpFamily. Only ipv4 or ipv6 are allowed"
        exit 1
  fi

  if [[ "${IP_FAMILY}" == "ipv6" ]] && [[ ! -z "${B64_CLUSTER_CA}" ]] && [[ ! -z "${APISERVER_ENDPOINT}" ]] && [[ -z "${SERVICE_IPV6_CIDR}" ]]; then
        echo "Service Ipv6 Cidr must be provided when ip-family is specified as IPV6"
        exit 1
  fi
fi

if [[ ! -z "${SERVICE_IPV6_CIDR}" ]]; then
     if [[ "${IP_FAMILY}" == "ipv4" ]]; then
            echo "ip-family should be ipv6 when service-ipv6-cidr is specified"
            exit 1
      fi
      IP_FAMILY="ipv6"
fi

echo "Aliasing EKS k8s snap commands"
snap alias kubelet-eks.kubelet kubelet
snap alias kubectl-eks.kubectl kubectl

echo "Stopping k8s daemons until configured"
snap stop kubelet-eks
# Flush the restart-rate for failed starts

AWS_DEFAULT_REGION=$(/usr/local/share/eks/imds 'latest/dynamic/instance-identity/document' | jq .region -r)
AWS_SERVICES_DOMAIN=$(/usr/local/share/eks/imds '2018-09-24/meta-data/services/domain')

MACHINE=$(uname -m)
if [[ "$MACHINE" != "x86_64" && "$MACHINE" != "aarch64" ]]; then
    echo "Unknown machine architecture '$MACHINE'" >&2
    exit 1
fi

ECR_URI=$(/etc/eks/get-ecr-uri.sh "${AWS_DEFAULT_REGION}" "${AWS_SERVICES_DOMAIN}" "${PAUSE_CONTAINER_ACCOUNT:-}")
PAUSE_CONTAINER_IMAGE=${PAUSE_CONTAINER_IMAGE:-$ECR_URI/eks/pause}
PAUSE_CONTAINER="$PAUSE_CONTAINER_IMAGE:$PAUSE_CONTAINER_VERSION"

### kubelet kubeconfig

CA_CERTIFICATE_DIRECTORY=/etc/kubernetes/pki
CA_CERTIFICATE_FILE_PATH=$CA_CERTIFICATE_DIRECTORY/ca.crt
mkdir -p $CA_CERTIFICATE_DIRECTORY
if [[ -z "${B64_CLUSTER_CA}" ]] || [[ -z "${APISERVER_ENDPOINT}" ]]; then
    DESCRIBE_CLUSTER_RESULT="/tmp/describe_cluster_result.txt"

    # Retry the DescribeCluster API for API_RETRY_ATTEMPTS
    for attempt in `seq 0 $API_RETRY_ATTEMPTS`; do
        rc=0
        if [[ $attempt -gt 0 ]]; then
            echo "Attempt $attempt of $API_RETRY_ATTEMPTS"
        fi

        aws eks wait cluster-active \
            --region=${AWS_DEFAULT_REGION} \
            --name=${CLUSTER_NAME}

        aws eks describe-cluster \
            --region=${AWS_DEFAULT_REGION} \
            --name=${CLUSTER_NAME} \
            --output=text \
            --query 'cluster.{certificateAuthorityData: certificateAuthority.data, endpoint: endpoint, serviceIpv4Cidr: kubernetesNetworkConfig.serviceIpv4Cidr, serviceIpv6Cidr: kubernetesNetworkConfig.serviceIpv6Cidr, clusterIpFamily: kubernetesNetworkConfig.ipFamily}' > $DESCRIBE_CLUSTER_RESULT || rc=$?
        if [[ $rc -eq 0 ]]; then
            break
        fi
        if [[ $attempt -eq $API_RETRY_ATTEMPTS ]]; then
            exit $rc
        fi
        jitter=$((1 + RANDOM % 10))
        sleep_sec="$(( $(( 5 << $((1+$attempt)) )) + $jitter))"
        sleep $sleep_sec
    done
    B64_CLUSTER_CA=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $1}')
    APISERVER_ENDPOINT=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $3}')
    SERVICE_IPV4_CIDR=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $4}')
    SERVICE_IPV6_CIDR=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $5}')

    if [[ -z "${IP_FAMILY}" ]]; then
      IP_FAMILY=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $2}')
    fi
fi

if [[ -z "${IP_FAMILY}" ]] || [[ "${IP_FAMILY}" == "None" ]]; then
       ### this can happen when the ifFamily field is not found in describeCluster response
       ### or B64_CLUSTER_CA and APISERVER_ENDPOINT are defined but IPFamily isn't
       IP_FAMILY="ipv4"
fi

echo $B64_CLUSTER_CA | base64 -d > $CA_CERTIFICATE_FILE_PATH

sed -i s,CLUSTER_NAME,$CLUSTER_NAME,g /var/lib/kubelet/kubeconfig
sed -i s,MASTER_ENDPOINT,$APISERVER_ENDPOINT,g /var/lib/kubelet/kubeconfig
sed -i s,AWS_REGION,$AWS_DEFAULT_REGION,g /var/lib/kubelet/kubeconfig
/snap/bin/kubectl config \
    --kubeconfig /var/lib/kubelet/kubeconfig \
    set-cluster \
    kubernetes \
    --certificate-authority=/etc/kubernetes/pki/ca.crt \
    --server=$APISERVER_ENDPOINT

### kubelet.service configuration

if [[ "${IP_FAMILY}" == "ipv6" ]]; then
      DNS_CLUSTER_IP=$(awk -F/ '{print $1}' <<< $SERVICE_IPV6_CIDR)a
fi

MAC=$(/usr/local/share/eks/imds 'latest/meta-data/mac')

if [[ -z "${DNS_CLUSTER_IP}" ]]; then
  if [[ ! -z "${SERVICE_IPV4_CIDR}" ]] && [[ "${SERVICE_IPV4_CIDR}" != "None" ]] ; then
    #Sets the DNS Cluster IP address that would be chosen from the serviceIpv4Cidr. (x.y.z.10)
    DNS_CLUSTER_IP=${SERVICE_IPV4_CIDR%.*}.10
  else
    TEN_RANGE=$(/usr/local/share/eks/imds "latest/meta-data/network/interfaces/macs/$MAC/vpc-ipv4-cidr-blocks" | grep -c '^10\..*' || true )
    DNS_CLUSTER_IP=10.100.0.10
    if [[ "$TEN_RANGE" != "0" ]]; then
      DNS_CLUSTER_IP=172.20.0.10
    fi
  fi
else
  DNS_CLUSTER_IP="${DNS_CLUSTER_IP}"
fi

KUBELET_CONFIG=/etc/kubernetes/kubelet/kubelet-config.json
kubelet_snap_add_options cluster-dns="$DNS_CLUSTER_IP"

if [[ "${IP_FAMILY}" == "ipv4" ]]; then
     INTERNAL_IP=$(/usr/local/share/eks/imds 'latest/meta-data/local-ipv4')
else
     INTERNAL_IP_URI=latest/meta-data/network/interfaces/macs/$MAC/ipv6s
     INTERNAL_IP=$(/usr/local/share/eks/imds $INTERNAL_IP_URI)
fi
INSTANCE_TYPE=$(/usr/local/share/eks/imds 'latest/meta-data/instance-type')

# Sets kubeReserved and evictionHard in /etc/kubernetes/kubelet/kubelet-config.json for worker nodes. The following two function
# calls calculate the CPU and memory resources to reserve for kubeReserved based on the instance type of the worker node.
# Note that allocatable memory and CPU resources on worker nodes is calculated by the Kubernetes scheduler
# with this formula when scheduling pods: Allocatable = Capacity - Reserved - Eviction Threshold.

#calculate the max number of pods per instance type
MAX_PODS_FILE="/etc/eks/eni-max-pods.txt"
set +o pipefail
MAX_PODS=$(cat $MAX_PODS_FILE | awk "/^${INSTANCE_TYPE:-unset}/"' { print $2 }')
set -o pipefail
if [ -z "$MAX_PODS" ] || [ -z "$INSTANCE_TYPE" ]; then
  log "INFO: No entry for type '$INSTANCE_TYPE' in $MAX_PODS_FILE. Will attempt to auto-discover value."
  # When determining the value of maxPods, we're using the legacy calculation by default since it's more restrictive than
  # the PrefixDelegation based alternative and is likely to be in-use by more customers.
  # The legacy numbers also maintain backwards compatibility when used to calculate `kubeReserved.memory`
  MAX_PODS=$(/etc/eks/max-pods-calculator.sh --instance-type-from-imds --cni-version 1.10.0 --show-max-allowed)
fi

# calculates the amount of each resource to reserve
mebibytes_to_reserve=$(get_memory_mebibytes_to_reserve $MAX_PODS)
cpu_millicores_to_reserve=$(get_cpu_millicores_to_reserve)
# writes kubeReserved and evictionHard to the kubelet-config using the amount of CPU and memory to be reserved
echo "$(jq '. += {"evictionHard": {"memory.available": "100Mi", "nodefs.available": "10%", "nodefs.inodesFree": "5%"}}' $KUBELET_CONFIG)" > $KUBELET_CONFIG
echo "$(jq --arg mebibytes_to_reserve "${mebibytes_to_reserve}Mi" --arg cpu_millicores_to_reserve "${cpu_millicores_to_reserve}m" \
    '. += {kubeReserved: {"cpu": $cpu_millicores_to_reserve, "ephemeral-storage": "1Gi", "memory": $mebibytes_to_reserve}}' $KUBELET_CONFIG)" > $KUBELET_CONFIG

if [[ "$USE_MAX_PODS" = "true" ]]; then
  echo "$(jq ".maxPods=$MAX_PODS" $KUBELET_CONFIG)" > $KUBELET_CONFIG
fi

if [[ "$CONTAINER_RUNTIME" = "containerd" ]]; then
    echo "Container runtime is containerd"
    mkdir -p /etc/systemd/system/containerd.service.d
    # Symlink is needed for pull-sandbox-image.sh
    cat <<EOF > /etc/systemd/system/containerd.service.d/10-compat-symlink.conf
[Service]
ExecStartPre=/bin/ln -sf /run/containerd/containerd.sock /run/dockershim.sock
EOF
    systemctl daemon-reload
    sed "s,SANDBOX_IMAGE,$PAUSE_CONTAINER,g" \
	    </usr/local/share/eks/containerd-config.toml \
	    >/etc/containerd/config.toml
    systemctl restart containerd
    /usr/local/share/eks/pull-sandbox-image.sh
    kubelet_snap_add_options \
        container-runtime=remote \
        container-runtime-endpoint=unix:///run/containerd/containerd.sock

elif [[ "$CONTAINER_RUNTIME" = "dockerd" ]]; then
    echo "Container runtime is docker"
    mkdir -p /etc/docker
    if [[ -n "$DOCKER_CONFIG_JSON" ]]; then
        echo "$DOCKER_CONFIG_JSON" > /etc/docker/daemon.json
    fi
    if [[ "$ENABLE_DOCKER_BRIDGE" = "true" ]]; then
          # Enabling the docker bridge network. We have to disable live-restore as it
          # prevents docker from recreating the default bridge network on restart
          echo "$(jq '.bridge="docker0" | ."live-restore"=false' /etc/docker/daemon.json)" > /etc/docker/daemon.json
    fi
    systemctl restart docker
    kubelet_snap_add_options \
        container-runtime=docker

elif [[ "$CONTAINER_RUNTIME" = "nvidia-container-runtime" ]]; then
    echo "Container runtime is ${CONTAINER_RUNTIME}"
    # update config.toml file
    # see https://github.com/NVIDIA/k8s-device-plugin
    cp /usr/local/share/eks/nvidia-runtime-config.toml /etc/containerd/config.toml
    systemctl restart containerd

else
    echo "Container runtime ${CONTAINER_RUNTIME} is not supported."
    exit 1
fi

if [[ "$CLOUD_PROVIDER" = "external" ]]; then
    echo "cloud-provider is $CLOUD_PROVIDER"
    # When the external cloud provider is used, kubelet will use /etc/hostname as the name of the Node object.
    # If the VPC has a custom `domain-name` in its DHCP options set, and the VPC has `enableDnsHostnames` set to `true`,
    # then /etc/hostname is not the same as EC2's PrivateDnsName.
    # The name of the Node object must be equal to EC2's PrivateDnsName for the aws-iam-authenticator to allow this kubelet to manage it.
    INSTANCE_ID=$(/usr/local/share/eks/imds /latest/meta-data/instance-id)
    REGION=$(/usr/local/share/eks/imds /latest/meta-data/placement/region)
    PRIVATE_DNS_NAME=$(AWS_RETRY_MODE=standard AWS_MAX_ATTEMPTS=10 aws ec2 describe-instances --region $REGION --instance-ids $INSTANCE_ID --query 'Reservations[].Instances[].PrivateDnsName' --output text)

    kubelet_snap_add_options \
         hostname-override=$PRIVATE_DNS_NAME \
         image-credential-provider-config=/etc/eks/ecr-credential-provider/config.json \
         image-credential-provider-bin-dir=/etc/eks/ecr-credential-provider
fi

# gpu boost clock
if  command -v nvidia-smi &>/dev/null && test "$CONTAINER_RUNTIME" = "nvidia-container-runtime"; then
   echo "nvidia-smi found"

   nvidia-smi -q > /tmp/nvidia-smi-check
   if [[ "$?" == "0" ]]; then
      sudo nvidia-smi -pm 1 # set persistence mode
      sudo nvidia-smi --auto-boost-default=0

      GPUNAME=$(nvidia-smi -L | head -n1)
      echo $GPUNAME

      # set application clock to maximum
      if [[ $GPUNAME == *"A100"* ]]; then
         nvidia-smi -ac 1215,1410
      elif [[ $GPUNAME == *"V100"* ]]; then
         nvidia-smi -ac 877,1530
      elif [[ $GPUNAME == *"K80"* ]]; then
         nvidia-smi -ac 2505,875
      elif [[ $GPUNAME == *"T4"* ]]; then
         nvidia-smi -ac 5001,1590
      elif [[ $GPUNAME == *"M60"* ]]; then
         nvidia-smi -ac 2505,1177
      else
         echo "unsupported gpu"
      fi
   else
      cat /tmp/nvidia-smi-check
   fi
else
    echo "nvidia-smi not found"
fi

kubelet_snap_add_options \
    address=0.0.0.0 \
    anonymous-auth=false \
    authentication-token-webhook=true \
    authorization-mode=Webhook \
    cgroup-driver=cgroupfs \
    client-ca-file="$CA_CERTIFICATE_FILE_PATH" \
    cloud-provider="$CLOUD_PROVIDER" \
    cluster-domain=cluster.local \
    cni-bin-dir=/opt/cni/bin \
    cni-conf-dir=/etc/cni/net.d \
    config="$KUBELET_CONFIG" \
    feature-gates=RotateKubeletServerCertificate=true \
    kubeconfig=/var/lib/kubelet/kubeconfig \
    node-ip="$INTERNAL_IP" \
    network-plugin=cni \
    register-node=true \
    resolv-conf=/run/systemd/resolve/resolv.conf \
    pod-infra-container-image="$PAUSE_CONTAINER" \
    args="$KUBELET_EXTRA_ARGS"

echo "Configuring kubelet snap"
kubelet_snap_configure

echo "Starting k8s kubelet daemon"
snap start --enable kubelet-eks
