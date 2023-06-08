#! /usr/bin/env bash

set -x
set -e

helm repo add jetstack https://charts.jetstack.io
helm repo add actions-runner-controller https://actions-runner-controller.github.io/actions-runner-controller
helm repo update

kubectl -n actions-runner-system delete -f lepton_runner_deployment.yaml

helm uninstall actions-runner-controller --namespace actions-runner-system

helm uninstall cert-manager  --namespace cert-manager
