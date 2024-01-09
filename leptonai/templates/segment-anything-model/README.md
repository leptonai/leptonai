# Segment Anything Model

This folder shows an end-to-end AI example, with Meta's most recent [Segment Anything](https://github.com/facebookresearch/segment-anything) model. Specifically, we will implement the functionality that takes an image and an optional prompt, and produces a segmentation mask, either as a list of structured boolean masks, or as a single overlayed image for display.

A quick example is shown below with input image and output mask:

<img src="assets/koala.jpeg" width=400><img src="assets/koala_segmented.jpg" width=400>

Technically, this demo shows how to:
- specify dependencies for a photon, including dependencies that are github repositories,
- use the `@Photon.handler` decorator to define handlers for a photon, and annotate the arguments and return values for better user experience,
- return different types of outputs from a photon deployment,
- use the python client to connect and interact with the deployment in nontrivial ways.

Check out `sam.py` for the actual implementation, and `segment-anything.ipynb` for a notebook demonstration.

To run it on Lepton AI platform, you can use the following command:

```bash
# Create a photon 
lep photon create -n sam -m py:github.com/leptonai/leptonai.git:leptonai/templates/segment-anything-model/sam.py
# Push the photon to the platform
lep photon push -n sam
# Run the SAM remotely
lep photon run -n sam --resource-shape gpu.a10
```
