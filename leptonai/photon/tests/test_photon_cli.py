from datetime import datetime
import os
import shutil
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from click.testing import CliRunner
from loguru import logger
import requests

from leptonai import config
from leptonai.photon import FileParam
from leptonai.photon.base import find_local_photon
from leptonai.cli import lep as cli
from utils import random_name, photon_run_local_server, sub_test, skip_if_macos


logger.info(f"Using cache dir: {config.CACHE_DIR}")


diffusers_model = "hf:hf-internal-testing/tiny-stable-diffusion-torch@a88cdfb"
transformers_model = "hf:sshleifer/tiny-gpt2@5f91d94"
whisper_model = "hf:openai/whisper-tiny.en"
summarization_model = "hf:jotamunz/billsum_tiny_summarization"
sentence_similarity_model = (
    "hf:sentence-transformers/paraphrase-albert-small-v2@b8a76dc"
)
text2text_generation_model = "hf:sshleifer/bart-tiny-random@69bce92"
sentiment_analysis_model = "hf:cross-encoder/ms-marco-TinyBERT-L-2-v2"
audio_classification_model = "hf:anton-l/wav2vec2-random-tiny-classifier"
depth_estimation_model = "hf:hf-tiny-model-private/tiny-random-GLPNForDepthEstimation"
microsoft_phi_model = "hf:microsoft/phi-1_5"
image_to_text_model = "hf:Salesforce/blip-image-captioning-base"
feature_extraction_model = "hf:hf-tiny-model-private/tiny-random-RobertaModel"


class TestPhotonCli(unittest.TestCase):
    def test_photon_create(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["photon", "create", "-m", diffusers_model])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--name", result.output.lower())

        # missing required --model option
        result = runner.invoke(cli, ["photon", "create", "-n", "abc"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--model", result.output.lower())

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abc", "-m", diffusers_model]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created", result.output)

    def test_photon_create_duplicate_name(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", diffusers_model]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created", result.output.lower())

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", diffusers_model]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created", result.output.lower())

    def test_photon_list(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcde", "-m", diffusers_model]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created", result.output.lower())

        result = runner.invoke(cli, ["photon", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("abcde", result.output.lower())
        # Check if the current time is in the output
        assert datetime.now().strftime("%Y-%m-%d") in result.output
        assert datetime.now().strftime("%H:%M") in result.output
        # Making sure that we don't make stupid errors and make the wrong
        # assumption about timestamp. No photon should have been created in 1970
        # and if we see that in the output, we know we used the wrong timestamp
        # granularity.
        self.assertNotIn("1970", result.output.lower())

        # Todo: actually this only checks whether the local
        # flag works, as we are not testing remote photons
        # yet.
        result = runner.invoke(cli, ["photon", "list", "--local"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("abcde", result.output.lower())

    def test_photon_remove(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcdef", "-m", diffusers_model]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("created", result.output.lower())

        result = runner.invoke(cli, ["photon", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("abcdef", result.output.lower())

        # when deleting local photons, must specify name
        result = runner.invoke(cli, ["photon", "remove"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--name", result.output.lower())

        result = runner.invoke(cli, ["photon", "remove", "-n", "abcdef"])
        self.assertEqual(result.exit_code, 0, result)
        self.assertIn("abcdef", result.output.lower())
        self.assertIn("removed", result.output.lower())

        result = runner.invoke(cli, ["photon", "remove", "-n", "abcdef"])
        assert result.exit_code == 1
        self.assertIn("abcdef", result.output.lower())

        result = runner.invoke(cli, ["photon", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("abcdef", result.output.lower())

    @skip_if_macos
    @sub_test([
        (diffusers_model,),
        (transformers_model,),
        # FIXME: these models need ffmpeg, but Github CI currently fails to
        # install it
        # (whisper_model,),
        # (audio_classification_model,),
        (summarization_model,),
        (sentence_similarity_model,),
        (text2text_generation_model,),
        (sentiment_analysis_model,),
        (depth_estimation_model,),
        (microsoft_phi_model,),
        (image_to_text_model,),
        (feature_extraction_model,),
    ])
    def test_photon_run(self, model):
        if os.getenv("GITHUB_ACTIONS") and model in [
            microsoft_phi_model,
            image_to_text_model,
        ]:
            logger.warning(f"Skipping {model} test on Github Actions")
            return

        name = random_name()
        proc, port = photon_run_local_server(name=name, model=model)

        # test example data
        openapi = requests.get(f"http://127.0.0.1:{port}/openapi.json").json()
        for path, endpoint in openapi["paths"].items():
            if "post" in endpoint:
                example = endpoint["post"]["requestBody"]["content"][
                    "application/json"
                ]["example"]

                # diffusers model takes too long to run, so overriding
                # num_inference_steps to 1 to make it run faster
                if model == diffusers_model:
                    example["num_inference_steps"] = 1

                res = requests.post(f"http://127.0.0.1:{port}{path}", json=example)
                if res.status_code != 200:
                    logger.warning(f"Failed to run {example} for {path}")
                    logger.warning(f"Client: {res.status_code} {res.text}")
                    logger.warning(f"Server: {proc.stdout.read().decode('utf-8')}")
                    logger.warning(f"Server: {proc.stderr.read().decode('utf-8')}")
                self.assertEqual(res.status_code, 200, res.text)
        proc.kill()

    @skip_if_macos
    def test_hf_embed(self):
        name = random_name()
        proc, port = photon_run_local_server(name=name, model=sentence_similarity_model)

        # single sentence
        res = requests.post(
            f"http://127.0.0.1:{port}/embed",
            json={
                "inputs": "This framework generates embeddings for each input sentence"
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        res = res.json()
        self.assertTrue(isinstance(res, list))
        self.assertTrue(isinstance(res[0], float))

        # batch
        inputs = [
            "A man is eating food.",
            "A man is eating a piece of bread.",
            "The girl is carrying a baby.",
            "A man is riding a horse.",
            "A woman is playing violin.",
            "Two men pushed carts through the woods.",
            "A man is riding a white horse on an enclosed ground.",
            "A monkey is playing drums.",
            "Someone in a gorilla costume is playing a set of drums.",
        ]
        res = requests.post(f"http://127.0.0.1:{port}/embed", json={"inputs": inputs})
        self.assertEqual(res.status_code, 200)
        res = res.json()
        self.assertTrue(isinstance(res, list))
        self.assertEqual(len(res), len(inputs))
        self.assertTrue(isinstance(res[0], list))
        self.assertTrue(isinstance(res[0][0], float))

        proc.kill()

    @skip_if_macos
    def test_photon_run_path(self):
        name = random_name()

        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", name, "-m", transformers_model]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue("created" in result.output)

        path = find_local_photon(name)
        self.assertIsNotNone(path)

        proc, port = photon_run_local_server(path=path)
        res = requests.post(
            f"http://127.0.0.1:{port}/run",
            json={"inputs": "a cat", "max_length": 10},
        )
        proc.kill()
        if res.status_code != 200:
            logger.warning(f"Client: {res.status_code} {res.text}")
            logger.warning(f"Server: {proc.stdout.read().decode('utf-8')}")
            logger.warning(f"Server: {proc.stderr.read().decode('utf-8')}")
        self.assertEqual(res.status_code, 200)

    @skip_if_macos
    @unittest.skipIf(not shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_photon_run_post_file(self):
        name = random_name()

        proc, port = photon_run_local_server(name=name, model=whisper_model)

        url = "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
        res_post_url = requests.post(
            f"http://127.0.0.1:{port}/run", json={"inputs": url}
        )

        content = requests.get(url).content
        res_post_file = requests.post(
            f"http://127.0.0.1:{port}/run",
            json={"inputs": {"content": FileParam.encode(content)}},
        )
        proc.kill()
        self.assertEqual(res_post_url.status_code, 200)
        self.assertEqual(res_post_file.status_code, 200)
        self.assertEqual(res_post_url.json(), res_post_file.json())

    @unittest.skipIf(not shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_photon_run_post_multi_files(self):
        name = random_name()

        proc, port = photon_run_local_server(
            name=name, model=audio_classification_model
        )

        url1 = "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
        url2 = "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/2.flac"
        res_post_url = requests.post(
            f"http://127.0.0.1:{port}/run",
            json={"inputs": [url1, url2]},
        )

        content1 = requests.get(url1).content
        content2 = requests.get(url2).content
        res_post_file = requests.post(
            f"http://127.0.0.1:{port}/run",
            json={
                "inputs": [
                    {"content": FileParam.encode(content1)},
                    {"content": FileParam.encode(content2)},
                ]
            },
        )
        proc.kill()
        self.assertEqual(res_post_url.status_code, 200)
        self.assertEqual(res_post_file.status_code, 200)
        self.assertEqual(res_post_url.json(), res_post_file.json())

    @skip_if_macos
    def test_photon_model_spec(self):
        import torch

        tmp = tempfile.NamedTemporaryFile(suffix=".py")
        with open(tmp.name, "w") as f:
            f.write("""
from leptonai.photon import Photon

class CustomPhoton(Photon):
    @Photon.handler
    def run(self, input: str) -> str:
        return "custom" + input
""")

        # (model str, valid)
        test_cases = [
            # with "py:" schema and class name
            (f"py:{tmp.name}:CustomPhoton", True),
            # no class name
            (f"py:{tmp.name}", True),
            # no "py:" schema
            (f"{tmp.name}:CustomPhoton", True),
            # just filename
            (tmp.name, True),
            # use variable
            ("leptonai.photon.prebuilt.Echo", True),
            # should specify class name when using variable
            ("leptonai.photon.prebuilt", False),
            # with "py:" schema
            ("py:leptonai.photon.prebuilt.Echo", True),
            # invalid
            (random_name(), False),
            ("nonexisting.py", False, "file"),
            # hf
            (transformers_model, True),
            # hf without "hf:"
            (transformers_model[3:], False),
            ("leptonai.photon.hf.hf.HuggingFacePhoton", False),
            ("leptonai.photon.hf.hf.HuggingfaceTextGenerationPhoton", False),
            # vllm model
            ("vllm:gpt2", True),
        ]

        cuda_available = torch.cuda.is_available()

        for test_case in test_cases:
            if len(test_case) == 2:
                model, valid = test_case
                msg = None
            else:
                model, valid, msg = test_case

            if model.startswith("vllm:") and not cuda_available:
                continue

            try:
                proc = None
                proc, _ = photon_run_local_server(name=random_name(), model=model)
            except Exception as e:
                self.assertFalse(valid, f"Model {model} should be valid")
                if msg is not None:
                    self.assertIn(msg, str(e))
            else:
                self.assertTrue(valid, f"Model {model} should be invalid")
            finally:
                if proc is not None:
                    proc.kill()

    def test_top_level_run_cmd(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "-h"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("runs a photon", result.output.lower())


if __name__ == "__main__":
    unittest.main()
