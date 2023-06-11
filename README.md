# lepton

## Dev and Staging environments

`dev-main`: For production. The main k8s cluster for production developments. Developers can deploy and test their changes as needed. The entry point for its `default` namespace is [dev-main.cloud.lepton.ai](http://dev-main.cloud.lepton.ai).

`dev-latest`: TODO (with latest code).

`dev-staging`: For pre-production and CD (continuous delivery) environments. When merging a PR to `main`, GitHub Actions will deploy the version to the `default` namespace of this k8s. The entry point is [dev-staging.cloud.lepton.ai](http://dev-staging.cloud.lepton.ai). You may access the latest but unstable features here.

`dev-ci`: For experiments and CI (continuous integrity) environments. When creating a PR, GitHub Actions will deploy `lepton-api-server` and `lepton-web` in a new namespace and run tests. Test files are in the `e2e-tests` folder. This cluster is only meant for CI. Do not rely on this cluster.
