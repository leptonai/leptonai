## Release Workflow

### A new major or minor version release

- Create a branch for the release. The branch name should be `release-<major>.<minor>-<date>`.

- Tag the commit in the release branch with the version in the format of `<major>.<minor>.<patch>`.

- Platform, CLI, and SDK release a new version based on this tag. The container image tag should match the release version. It is OK to add build info after the `-`` and add some prefixes that clearly separate from SemVer.

For individual, uncoordinated releases of infra backend / web frontend / python SDK, the release tag can be created from the latest commit in the master branch, and then do an individual release. However, if you do so, make sure the API interfaces are compatible under the same major and minor version, across the three major components. For API-breakinng changes, always do a coordinated release.

### A new patch release

- Cherry-pick the required patches into the target release branch.

- Tag the last commit with the version in the format of `<target-branch-major>.<target-branch-minor>.<prev-patch + 1>`.

- Platform, CLI, and SDK release a new version based on this tag. The container image tag should match the release version. It is OK to add build info after the `-` and add some prefixs that clearly separate from SemVer.

### Note

- Please do not add `v` as a prefix. See https://semver.org/#is-v123-a-semantic-version

- Please always check if the version is valid. Use https://regex101.com/r/Ly7O1x/3/.

## Releasing an SDK & CLI python package
- First make sure the git tag is properly attached to the corresponding git commit. e.g. do `git log 0.5.0 -n 1`
- Go to https://github.com/leptonai/lepton/actions/workflows/sdk-release.yaml
- Click "Run workflow" button on the top right corner, it will pop up a drop down menu
  - In the "Use workflow from" field, choose "tags" (instead of "branches"), and enter the version number that is being released (e.g. 0.5.0)
  - Check the "Whether publish to S3" and "Is this a release package" checkboxes, and click "Run workflow"
- The workflow will go through "build-package", "test-package" and "publish-package" jobs. Once all done, you can find the corresponding `.whl` file at the `lepton-sdk` s3 bucket under "release" subdirectory: https://s3.console.aws.amazon.com/s3/buckets/lepton-sdk?region=us-east-1&tab=objects

If you update the SDK, you will also need to update the container image. See below.

### Pushing a new version to container registry

Right now, Lepton SDK is pre-shipped with the container image. This means that if you make a backward-breaking change, you will need to redeploy the container image as well. This might change after we do regular public releases of Lepton, and will pull Lepton sdk dyamically. For now, follow the steps here:

#### Create Image
Make sure that you are on a cleanly committed and pushed branch, say `myimage`. Check out that branch, bump the image version from the [leptonai/config.py](https://github.com/leptonai/lepton/blob/main/sdk/leptonai/config.py) file, for example bump it to "0.7.2". Commit and push this change too.

Try to use the same version number as the main lepton version - this means, if you update the container image, you might also want to release a new SDK version.

Go to github workflows and find the "Build and Deploy Photon Runner Docker Images" action [here](https://github.com/leptonai/lepton/actions/workflows/photon-runner-docker-images.yaml). Select "Run workflow", choose the branch as the one you use (in our case, `myimage`), and use the image version you bumped (like "0.7.2") as the Photon Runner Version. Run the workflow.

#### Create a pull request.

Make a pull request and merge it. Voila!

Note that these changes are backward compatible. Older photons are configured to use older images, which are always preserved.
