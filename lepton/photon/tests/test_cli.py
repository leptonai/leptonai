import os
import tempfile

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from click.testing import CliRunner
from loguru import logger
import requests
from textwrap import dedent

from lepton import config
from lepton.photon.base import find_photon
from lepton.cli import lepton as cli
from utils import random_name, photon_run_server, sub_test


logger.info(f"Using cache dir: {config.CACHE_DIR}")


diffusers_model = (
    "hf:runwayml/stable-diffusion-v1-5",
    {"prompt": "a cat", "num_inference_steps": 2},
)
transformers_model = ("hf:gpt2", {"inputs": "a cat", "max_length": 10})
whisper_model = (
    "hf:openai/whisper-tiny.en",
    {"inputs": "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"},
)
wav2vec2_model = (
    "hf:jonatasgrosman/wav2vec2-large-xlsr-53-english",
    {"inputs": "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"},
)
wikihow_t5_model = (
    "hf:facebook/bart-large-cnn",
    {
        "inputs": dedent(
            """ The tower is 324 metres (1,063 ft) tall, about the same
height as an 81-storey building, and the tallest structure in Paris. Its base
is square, measuring 125 metres (410 ft) on each side. During its construction,
the Eiffel Tower surpassed the Washington Monument to become the tallest
man-made structure in the world, a title it held for 41 years until the
Chrysler Building in New York City was finished in 1930. It was the first
structure to reach a height of 300 metres. Due to the addition of a
broadcasting aerial at the top of the tower in 1957, it is now taller than the
Chrysler Building by 5.2 metres (17 ft). Excluding transmitters, the Eiffel
Tower is the second tallest free-standing structure in France after the Millau
Viaduct.  """,
        ),
    },
)

sentence_similarity_model = (
    "hf:sentence-transformers/all-mpnet-base-v2",
    {
        "source_sentence": "A cat",
        "sentences": [
            "The cat sat on the mat.",
            "The dog lay on the rug.",
            "The fox slept on the haystack.",
        ],
    },
)


class TestPhotonCli(unittest.TestCase):
    def test_photon_create(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["photon", "create", "-m", diffusers_model[0]])
        assert result.exit_code != 0
        assert "--name" in result.output.lower()

        # missing required --model option
        result = runner.invoke(cli, ["photon", "create", "-n", "abc"])
        assert result.exit_code != 0
        assert "--model" in result.output.lower()

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abc", "-m", diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output

    def test_photon_create_duplicate_name(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_photon_list(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcde", "-m", diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(cli, ["photon", "list"])
        assert result.exit_code == 0
        assert "abcde" in result.output.lower()

    def test_photon_remove(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcdef", "-m", diffusers_model[0]]
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

    @sub_test(
        [
            diffusers_model,
            transformers_model,
            # FIXME: this model needs ffmpeg, but Github CI currently fails to install it
            # whisper_model,
            wikihow_t5_model,
            sentence_similarity_model,
        ]
    )
    def test_photon_run(self, model, json):
        name = random_name()
        proc, port = photon_run_server(name=name, model=model)
        res = requests.post(
            f"http://127.0.0.1:{port}/run",
            json=json,
        )
        proc.kill()

        if res.status_code != 200:
            logger.warning(f"Client: {res.status_code} {res.text}")
            logger.warning(f"Server: {proc.stdout.read().decode('utf-8')}")
            logger.warning(f"Server: {proc.stderr.read().decode('utf-8')}")
        self.assertEqual(res.status_code, 200)

    def test_hf_embed(self):
        name = random_name()
        proc, port = photon_run_server(name=name, model=sentence_similarity_model[0])

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
            cli, ["photon", "create", "-n", name, "-m", transformers_model[0]]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue("created" in result.output)

        path = find_photon(name)
        self.assertIsNotNone(path)

        proc, port = photon_run_server(path=path, model=transformers_model[0])
        res = requests.post(
            f"http://127.0.0.1:{port}/run",
            json=transformers_model[1],
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
            proc, port = photon_run_server(name=name, model=model[0])
            with tempfile.NamedTemporaryFile() as f:
                f.write(requests.get(model[1]["inputs"]).content)
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
