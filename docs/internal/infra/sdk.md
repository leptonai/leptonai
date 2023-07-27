# SDK related topics

## Publishing new SDK to pypi/conda

To be written

## Pushing a new version to container registry

Right now, Lepton SDK is pre-shipped with the container image. This means that if you make a backward-breaking change, you will need to redeploy the container image as well. This might change after we do regular public releases of Lepton, and will pull Lepton sdk dyamically. For now, follow the steps here:

### Create Image
Make sure that you are on a cleanly committed and pushed branch, say `myimage`. Check out that branch, bump the image version from the [leptonai/config.py](https://github.com/leptonai/lepton/blob/main/sdk/leptonai/config.py) file, for example bump it to "0.1.12". Commit and push this change too.

Go to github workflows and find the "Build and Deploy Photon Runner Docker Images" action [here](https://github.com/leptonai/lepton/actions/workflows/photon-runner-docker-images.yaml). Select "Run workflow", choose the branch as the one you use (in our case, `myimage`), and use the image version you bumped (like "0.1.12") as the Photon Runner Version. Run the workflow.

### Create a pull request.

Make a pull request and merge it. Voila!

Note that these changes are backward compatible. Older photons are configured to use older images, which are always preserved.