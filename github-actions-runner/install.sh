#! /usr/bin/env bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <github_token>"
  exit 1
fi

github_token=$1

set -x
set -e

helm repo add jetstack https://charts.jetstack.io
helm repo add actions-runner-controller https://actions-runner-controller.github.io/actions-runner-controller
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

helm upgrade --install actions-runner-controller actions-runner-controller/actions-runner-controller \
  --namespace actions-runner-system \
  --create-namespace \
  --set=authSecret.create=true \
  --set=authSecret.github_token="${github_token}" \
  --set "githubWebhookServer.enabled=true,service.type=NodePort,githubWebhookServer.ports[0].nodePort=33080" \
  --wait

kubectl -n actions-runner-system apply -f lepton_runner_deployment.yaml
