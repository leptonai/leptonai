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
