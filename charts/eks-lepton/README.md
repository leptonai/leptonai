# Lepton Helm Chart

Run the following command to install lepton cluster-level charts (CRDs, etc)

```sh
helm install lepton-crd . --namespace default --set awsCreds.creds=$AWS_CREDS
```
