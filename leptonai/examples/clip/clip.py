"""
This is a simple class that shows how to use the Photon SDK to create a
common embedding service for text and image (assuming image urls), using the
CLIP model. Note that for the sake of simplicity, the model is downloaded from
the internet every time the photon is run. This is not recommended for
production use though, but is fine if you are running prototypes.

In default, this uses the ViT-B-32-quickgelu model with the laion400m_e32 pretrained weights.
You can change the model and pretrained weights by passing in the MODEL_NAME and PRETRAINED
environment variables when running the photon. However, we do not proactively sanity
check the validity of the specified model name and pretrained weights name, so please
make sure they are valid.

To build the photon, do:

    lep photon create -n clip -m clip.py:Clip

To run the photon locally, simply do

    lep photon run -n clip --local

For other models, you can try adding --env arguments like:

    --env DEFAULT_MODEL_NAME=ViT-B-32-quickgelu --env DEFAULT_PRETRAINED=laion400m_e32

and the list of models can be found at
    https://github.com/mlfoundations/open_clip/blob/main/src/open_clip/pretrained.py

To deploy the photon, do

    lep photon push -n clip
    lep photon run -n clip -dn clip

Or choose your own deployment name like "-dn my-clip-deployment".

To test the photon, you can either use the API explorer in the UI, or use
the photon client class in python, e.g.

    from leptonai.client import Client
    # If you are runnnig the photon remotely with workspace name "myworkspace"
    # and deployment name "clip"
    client = Client("myworkspace", "clip")
    # Or if you are running the photon locally at port 8080
    client = Client("http://localhost:8080")
    # Do NOT run the above two commands at the same time! Choose only one.

    # Now you can call the endpoints
    vec = client.embed(query="people running by the sea"))
    # Or call explicit functions:
    vec = client.embed_text(query="people running by the sea"))
    vec = client.embed_image(url="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Fermilab.jpg/800px-Fermilab.jpg")
"""

import io
import os
import urllib
from typing import List

import open_clip
from PIL import Image
import torch
import validators

from leptonai.photon import Photon, handler, HTTPException


DEFAULT_MODEL_NAME = "ViT-B-32-quickgelu"
DEFAULT_PRETRAINED = "laion400m_e32"


class Clip(Photon):
    """
    This photon is used to embed text and image into a vector space using CLIP.
    """

    # Python dependency
    requirement_dependency = [
        "open_clip_torch",
        "Pillow",
        "torch",
        "transformers",
        "validators",
    ]

    def init(self):
        if torch.cuda.is_available():
            self.DEVICE = "cuda"
        else:
            self.DEVICE = "cpu"
        MODEL_NAME = (
            os.environ["MODEL_NAME"]
            if "MODEL_NAME" in os.environ
            else DEFAULT_MODEL_NAME
        )
        PRETRAINED = (
            os.environ["PRETRAINED"]
            if "PRETRAINED" in os.environ
            else DEFAULT_PRETRAINED
        )
        (
            self.CLIP_MODEL,
            _,
            self.CLIP_IMG_PREPROCESS,
        ) = open_clip.create_model_and_transforms(
            model_name=MODEL_NAME, pretrained=PRETRAINED, device=self.DEVICE
        )
        self.TOKENIZER = open_clip.get_tokenizer(MODEL_NAME)

    @handler("embed")
    def embed(self, query: str) -> List[float]:
        if validators.url(query):
            return self.embed_image(query)
        else:
            return self.embed_text(query)

    @handler("embed_text")
    def embed_text(self, query: str) -> List[float]:
        query = self.TOKENIZER([query])
        with torch.no_grad():
            text_features = self.CLIP_MODEL.encode_text(query.to(self.DEVICE))
            text_features /= text_features.norm(dim=-1, keepdim=True)
        return list(text_features.cpu().numpy()[0].astype(float))

    def embed_image_local(self, image: Image):
        image = self.CLIP_IMG_PREPROCESS(image).unsqueeze(0).to(self.DEVICE)
        with torch.no_grad():
            image_features = self.CLIP_MODEL.encode_image(image)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        return list(image_features.cpu().numpy()[0].astype(float))

    @handler("embed_image")
    def embed_image(self, url: str) -> List[float]:
        # open the imageurl and then read the content into a buffer
        try:
            raw_img = Image.open(io.BytesIO(urllib.request.urlopen(url).read()))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot open image at url {url}. Detailed error message: {str(e)}"
                ),
            )
        return self.embed_image_local(raw_img)
