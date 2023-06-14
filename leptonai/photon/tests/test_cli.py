import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from click.testing import CliRunner
from loguru import logger
import requests

from leptonai import config
from leptonai.photon.base import find_photon
from leptonai.cli import lep as cli
from utils import random_name, photon_run_server, sub_test


logger.info(f"Using cache dir: {config.CACHE_DIR}")


diffusers_model = "hf:runwayml/stable-diffusion-v1-5"
transformers_model = "hf:gpt2"
whisper_model = "hf:openai/whisper-tiny.en"
wav2vec2_model = "hf:jonatasgrosman/wav2vec2-large-xlsr-53-english"
wikihow_t5_model = "hf:facebook/bart-large-cnn"
sentence_similarity_model = "hf:sentence-transformers/all-mpnet-base-v2"
flan_t5_model = "hf:google/flan-t5-small"


class TestPhotonCli(unittest.TestCase):
    def test_photon_create(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["photon", "create", "-m", diffusers_model])
        assert result.exit_code != 0
        assert "--name" in result.output.lower()

        # missing required --model option
        result = runner.invoke(cli, ["photon", "create", "-n", "abc"])
        assert result.exit_code != 0
        assert "--model" in result.output.lower()

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abc", "-m", diffusers_model]
        )
        assert result.exit_code == 0
        assert "created" in result.output

    def test_photon_create_duplicate_name(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", diffusers_model]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", diffusers_model]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_photon_list(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcde", "-m", diffusers_model]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(cli, ["photon", "list"])
        assert result.exit_code == 0
        assert "abcde" in result.output.lower()

    def test_photon_remove(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcdef", "-m", diffusers_model]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(cli, ["photon", "list"])
        assert result.exit_code == 0
        assert "abcdef" in result.output.lower()

        # when deleting local photons, must specify name
        result = runner.invoke(cli, ["photon", "remove"])
        assert result.exit_code != 0
        assert "--name" in result.output.lower()

        result = runner.invoke(cli, ["photon", "remove", "-n", "abcdef"])
        assert result.exit_code == 0
        assert "abcdef" in result.output.lower()
        assert "removed" in result.output.lower()

        result = runner.invoke(cli, ["photon", "remove", "-n", "abcdef"])
        assert result.exit_code == 1
        assert "abcdef" in result.output.lower()

        result = runner.invoke(cli, ["photon", "list"])
        assert result.exit_code == 0
        assert "abcdef" not in result.output.lower()

    @unittest.skipIf(os.environ.get("GITHUB_ACTIONS"), "Skip on Github CI, too slow")
    @sub_test(
        [
            (diffusers_model,),
            (transformers_model,),
            # FIXME: this model needs ffmpeg, but Github CI currently fails to
            # install it
            # (whisper_model,),
            (wikihow_t5_model,),
            (sentence_similarity_model,),
            (flan_t5_model,),
        ]
    )
    def test_photon_run(self, model):
        name = random_name()
        proc, port = photon_run_server(name=name, model=model)

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
        proc, port = photon_run_server(name=name, model=sentence_similarity_model)

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

        path = find_photon(name)
        self.assertIsNotNone(path)

        proc, port = photon_run_server(path=path, model=transformers_model)
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

    @unittest.skip("FIXIT: pydantic doesn't support file type")
    def test_photon_run_post_file(self):
        name = random_name()

        for model in [self.wav2vec2_model, self.whisper_model]:
            proc, port = photon_run_server(name=name, model=model)
            with tempfile.NamedTemporaryFile() as f:
                f.write(
                    requests.get(
                        "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
                    ).content
                )
                f.flush()
                f.seek(0)
                res = requests.post(
                    f"http://127.0.0.1:{port}/run",
                    data=f.read(),
                )
            proc.kill()

            if res.status_code != 200:
                logger.warning(f"Client: {res.status_code} {res.text}")
                logger.warning(f"Server: {proc.stdout.read().decode('utf-8')}")
                logger.warning(f"Server: {proc.stderr.read().decode('utf-8')}")
            self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
