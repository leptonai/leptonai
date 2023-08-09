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
from leptonai.cli import photon as photon_cli
from leptonai.photon.tests.utils import random_name, photon_run_local_server, sub_test


logger.info(f"Using cache dir: {config.CACHE_DIR}")


diffusers_model = "hf:hf-internal-testing/tiny-stable-diffusion-torch@a88cdfb"
transformers_model = "hf:sshleifer/tiny-gpt2@5f91d94"
whisper_model = "hf:openai/whisper-tiny.en"
summarization_model = "hf:facebook/bart-large-cnn"
sentence_similarity_model = (
    "hf:sentence-transformers/paraphrase-albert-small-v2@b8a76dc"
)
text2text_generation_model = "hf:sshleifer/bart-tiny-random@69bce92"
sentiment_analysis_model = "hf:cross-encoder/ms-marco-TinyBERT-L-2-v2"
audio_classification_model = "hf:anton-l/wav2vec2-random-tiny-classifier"


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
        self.assertEqual(result.exit_code, 0)
        self.assertIn("abcdef", result.output.lower())
        self.assertIn("removed", result.output.lower())

        result = runner.invoke(cli, ["photon", "remove", "-n", "abcdef"])
        assert result.exit_code == 1
        self.assertIn("abcdef", result.output.lower())

        result = runner.invoke(cli, ["photon", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("abcdef", result.output.lower())

    @sub_test(
        [
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
        ]
    )
    def test_photon_run(self, model):
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
                self.assertEqual(res.status_code, 200)
        proc.kill()

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
        self.assertEqual(res.status_code, 200)
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

        proc, port = photon_run_local_server(path=path, model=transformers_model)
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

    def test_parse_photon_token_config(self):
        # public token
        tokens = photon_cli._parse_deployment_tokens_or_die(True, None)
        self.assertEqual(tokens, [])
        tokens = photon_cli._parse_deployment_tokens_or_die(True, [])
        self.assertEqual(tokens, [])
        tokens = photon_cli._parse_deployment_tokens_or_die(False, None)
        self.assertEqual(
            tokens, [{"value_from": {"token_name_ref": "WORKSPACE_TOKEN"}}]
        )
        tokens = photon_cli._parse_deployment_tokens_or_die(False, ["abc", "def"])
        self.assertEqual(
            tokens,
            [
                {"value_from": {"token_name_ref": "WORKSPACE_TOKEN"}},
                {"value": "abc"},
                {"value": "def"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
