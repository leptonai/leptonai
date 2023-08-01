## Release Workflow

### A new major or minor version release

- Create a branch for the release. The branch name should be `release-<major>.<minor>-<date>`.

- Tag the commit in the release branch with the version in the format of `<major>.<minor>.<patch>`.

- Platform, CLI, and SDK release a new version based on this tag. The container image tag should match the release version. It is OK to add build info after the `-`` and add some prefixes that clearly separate from SemVer.

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
- The workflow will go through "build-package", "test-package" and "publish-package" jobs. Once all done, you can find the corresponding `.whl` file at the `lepton-sdk` s3 bucket under "release" subdirectory
