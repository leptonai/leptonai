import base64
import hashlib
import os
import unittest

import requests

from leptonai.client import Client
from leptonai.photon import FileParam

API_URL = os.environ.get("SDXL_API_URL", "http://localhost:8080")


class TestInpaint(unittest.TestCase):
    def setUp(self):
        self.client = Client(API_URL)

        self.prompt = "A cat sitting on a bench"
        self.seed = 1234
        self.img_url = "https://raw.githubusercontent.com/CompVis/latent-diffusion/main/data/inpainting_examples/overture-creations-5sI6fQgYIuo.png"
        self.mask_url = "https://raw.githubusercontent.com/CompVis/latent-diffusion/main/data/inpainting_examples/overture-creations-5sI6fQgYIuo_mask.png"
        self.img_content = requests.get(self.img_url).content
        self.mask_content = requests.get(self.mask_url).content

    def test_inpaint_url(self):
        result = self.client.inpaint(
            prompt=self.prompt,
            seed=self.seed,
            image=self.img_url,
            mask_image=self.mask_url,
        )
        with open("inpaint_url.png", "wb") as f:
            f.write(result)

    def test_inpaint_fileparam(self):
        result = self.client.inpaint(
            prompt=self.prompt,
            seed=self.seed,
            image=FileParam(self.img_content),
            mask_image=FileParam(self.mask_content),
        )
        with open("inpaint_fileparam.png", "wb") as f:
            f.write(result)

    def test_inpaint_base64(self):
        res = requests.post(
            f"{API_URL}/inpaint",
            json={
                "prompt": self.prompt,
                "seed": self.seed,
                "image": base64.b64encode(self.img_content).decode("utf-8"),
                "mask_image": base64.b64encode(self.mask_content).decode("utf-8"),
            },
        )
        res.raise_for_status()
        with open("inpaint_base64.png", "wb") as f:
            f.write(res.content)

    def test_results_consistency(self):
        # check three images' md5sum are the same

        # md5sum of url image
        with open("inpaint_url.png", "rb") as f:
            url_md5 = hashlib.md5(f.read()).hexdigest()

        # md5sum of fileparam image
        with open("inpaint_fileparam.png", "rb") as f:
            fileparam_md5 = hashlib.md5(f.read()).hexdigest()

        # md5sum of base64 image
        with open("inpaint_base64.png", "rb") as f:
            base64_md5 = hashlib.md5(f.read()).hexdigest()

        self.assertEqual(url_md5, fileparam_md5)
        self.assertEqual(url_md5, base64_md5)

    def test_inpaint_with_refiner(self):
        result = self.client.inpaint(
            prompt=self.prompt,
            seed=self.seed,
            image=self.img_url,
            mask_image=self.mask_url,
            use_refiner=True,
        )
        with open("inpaint_with_refiner.png", "wb") as f:
            f.write(result)


if __name__ == "__main__":
    unittest.main()
