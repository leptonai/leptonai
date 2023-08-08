import io
import os
import requests
from urllib.request import urlopen

from typing import Optional
from loguru import logger

import numpy as np
from PIL import Image

from leptonai.photon import Photon, HTTPException, PNGResponse
from leptonai.photon.types import lepton_pickle, LeptonPickled

from segment_anything import SamAutomaticMaskGenerator, SamPredictor, sam_model_registry
import torch


class SAM(Photon):
    """
    This is a demo photon to show how one can wrap a nontrivial model, in this case
    the SAM (segment anything model), using the leptonai sdk. Please refer to the
    comments in the code for more details.
    """

    # Requirement_dependency specifies what kind of dependencies need to be installed when
    # running the photon in the cloud. Note that this can be standard python pip packages,
    # or it can be a git repo. In this case, we need to install the segment-anything
    # package, which is a git repo. We also need to install Pillow, which is a standard
    # python package.
    requirement_dependency = [
        "git+https://github.com/facebookresearch/segment-anything.git",
        "Pillow",
    ]

    # Similar to regular python, you can add custom member variables to the photon class.
    # In this case, we will specify where we can download the checkpoint for the model.
    # We will also specify where we will cache the checkpoint.
    checkpoints = {
        "vit_h": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        "vit_l": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
        "vit_b": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
    }

    def init(self):
        """
        The init function is called when the photon is first loaded. This is where
        you can load the model checkpoint, and do any other initialization work.
        """
        # We will first check if the model type is specified. When you run a photon,
        # you can pass in environment variables, which is usually a good way to
        # pass in configurations. In this case, we will use the MODEL_TYPE environment
        # variable to specify which model we want to use. If the environment variable
        # is not specified, we will use the vit_h model.
        #
        # During execution time, you can specify e.g. --env MODEL_TYPE=vit_l to use
        # the vit_l model. Please refer to the documentation for more details about
        # env variables:
        #       https://www.lepton.ai/docs/advanced/env_n_secrets
        self.model_type = os.environ.get("MODEL_TYPE", "vit_h")

        # We will explicitly specify a cache folder for the checkpoint. Note that
        # if we specify a local folder, the download will be ephemeral - if the
        # photon is restarted, the checkpoint will be downloaded again. Lepton
        # does provide a persistent storage solution where every deployment can mount as
        # a standard NFS volume - the recommended way is to mount it on /opt/leptonstore.
        # We can then use the environment variable CACHE_FOLDER to tell the photon to
        # read from and write to  the cache folder. If we use this method, we run
        # the photon with
        #     --mount /:/opt/leptonstore --env CACHE_FOLDER=/opt/leptonstore/sem-checkpoint
        # If the local cache folder is not specified, we will use '/tmp/sem-checkpoint'.
        #
        # Please refer to the documentation for more details:
        #       https://www.lepton.ai/docs/advanced/storage
        self.local_cache_folder = os.environ.get("CACHE_FOLDER", "/tmp/sem-checkpoint")

        # Below is the utility code that downloads the checkpoint. Nothing fancy here,
        # just standard python code.
        checkpoint_url = self.checkpoints[self.model_type]
        target_checkpoint_path = os.path.join(
            self.local_cache_folder, os.path.basename(checkpoint_url)
        )
        if not os.path.exists(target_checkpoint_path):
            logger.info(
                f"Downloading checkpoint from {checkpoint_url} to"
                f" {target_checkpoint_path}."
            )
            # We will download the checkpoint to the local cache folder
            os.makedirs(self.local_cache_folder, exist_ok=True)
            # Download the checkpoint url to the local cache folder
            # You can use any method to download the checkpoint
            # For example, you can use `requests` or `wget`
            # Here we use requests.
            response = requests.get(checkpoint_url)
            with open(target_checkpoint_path, "wb") as f:
                f.write(response.content)
        else:
            logger.info(
                f"Checkpoint already exists at {target_checkpoint_path}. Reusing it."
            )

        # Now let's actually load the checkpoint. We'll load this into a member
        # variable `sam`, so that we can use it later.
        self.sam = sam_model_registry[self.model_type](
            checkpoint=target_checkpoint_path
        )

        # Check if we need to go to GPU. Torch provides a convenient way to check
        # if cuda is available - let's use that.
        if torch.cuda.is_available():
            self.sam.to(device="cuda")

        # Similar to SAM's model itself, we will also create a predictor and a mask
        # generator. We will use these later.
        self.predictor = SamPredictor(self.sam)
        self.mask_generator = SamAutomaticMaskGenerator(self.sam)

    # @Photon.handler() is a decorator that tells lepton that this function is
    # going to be exposed as an API endpoint. If no path is specified, the endpoint
    # name will be the same as the function name. In this case, the endpoint name
    # will be predict_url.
    #
    # The example field is optional, but it is recommended to provide an example
    # request. When you use the leptonai sdk or web UI, the examples will help the
    # user understand how to use your photon.
    #
    # For the funciton itself, it is recommended that you type annotate the inputs
    # and outputs. This will make it easier for lepton to generate the client side
    # documentation.
    @Photon.handler(
        "predict_url",
        example={
            "url": "https://upload.wikimedia.org/wikipedia/commons/4/49/Koala_climbing_tree.jpg",
            "prompt": "Please segment the koala.",
        },
    )
    def predict_url(self, url: str, prompt: Optional[str] = None) -> LeptonPickled:
        """
        This is the predict_url endpoint. It takes in an image url, calls the mask generator, and
        returns the masks. We also do proper error handling here: if the image cannot opened, or
        if the mask cannot be generated, we will return a proper http error back to the user side.
        """

        # We will first download the image from the url. We will use the standard python
        # urllib to do this. Note that this is just an example - you can use any method
        # to download the image.
        try:
            raw_img = np.asarray(Image.open(io.BytesIO(urlopen(url).read())))
        except Exception as e:
            # HTTPException is a special exception that will be translated to a proper
            # http error by fastAPI and return to the user side. In this case, we will
            # return a 400 error code as the image cannot be opened.
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot open image at url {url}. Detailed error message: {str(e)}"
                ),
            )

        # Actually run the model. Just to be safe, we wrap this function inside a try-catch
        # block. If the model fails to run, we will return a 500 error code telling the user
        # that the model failed to run.
        try:
            masks = self.mask_generator.generate(raw_img)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Cannot generate mask for image at url {url}. Detailed error"
                    f" message: {str(e)}"
                ),
            )

        # Now, when the model runs successfully, we will return the masks. Segment-anything
        # model right now returns a complex data structure that is not immediately sendable
        # over the network. Usually, python web service interfaces don't really support complex
        # data structures, and only send simple types like int, float, string, etc. For more
        # details, please refer to the fastAPI documentation here:
        #      https://fastapi.tiangolo.com/python-types/
        # As a result, you will need to usually adopt a serialziation strategy. There are
        # many ways to do this, such as protocol buffer, thrift, json, etc.
        #
        # As a demonstrative example, leptonai sdk provides a simple serialization method
        # based on python pickle. This can be used for simple data structures. In this case,
        # the server side pickles the data, and on the client side, one can use lepton_unpickle
        # to recover the actual data structure.
        #
        # Note that pickle comes with its own security risks - it may contain arbitrary code,
        # and it is prone to error when the client and server side are not using the same
        # python version. In real production scenarios, you might want to use a more robust
        # serialization method.
        return lepton_pickle(masks, compression=9)

    @Photon.handler(
        "generate_mask",
        example={
            "url": "https://upload.wikimedia.org/wikipedia/commons/4/49/Koala_climbing_tree.jpg",
            "prompt": "Please segment the koala.",
        },
    )
    def generate_mask(self, url: str, prompt: Optional[str] = None) -> PNGResponse:
        """
        Generates a mask image for the segmentation result. This is similar to the predict_url
        endpoint, except that we will return a mask image instead of a python array of the raw
        masks.
        """
        try:
            raw_img = np.asarray(Image.open(io.BytesIO(urlopen(url).read())))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot open image at url {url}. Detailed error message: {str(e)}"
                ),
            )
        try:
            masks = self.mask_generator.generate(raw_img)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Cannot generate mask for image at url {url}. Detailed error"
                    f" message: {str(e)}"
                ),
            )

        # The below rendering code is copied from the segment-anything repo to draw the mask
        # on top of the original image.
        sorted_anns = sorted(masks, key=(lambda x: x["area"]), reverse=True)
        mask_img = np.ones(
            (
                sorted_anns[0]["segmentation"].shape[0],
                sorted_anns[0]["segmentation"].shape[1],
                3,
            )
        )
        for ann in sorted_anns:
            mask_img[ann["segmentation"]] = np.random.random(3)
        alpha = 0.35
        img = mask_img * alpha + (raw_img.astype(float) / 255) * (1 - alpha)
        # Convert the img numpy class to an image io that we can use to send back to the client
        img = Image.fromarray((img * 255).astype(np.uint8))
        img_byte_array = io.BytesIO()
        img.save(img_byte_array, format="PNG")
        img_byte_array.seek(0)
        # In this case, we will use the PNGResponse class provided by leptonai sdk to send
        # the image back to the client. This is a convenience class that will set the
        # correct content type for the response.
        return PNGResponse(img_byte_array)
