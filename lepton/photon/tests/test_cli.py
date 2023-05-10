import os
import tempfile
from utils import random_name, photon_run_server

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

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestPhotonCli(unittest.TestCase):
    diffusers_model = (
        "hf:runwayml/stable-diffusion-v1-5",
        {"prompt": "a cat", "num_inference_steps": 2},
    )
    transformers_model = ("hf:gpt2", {"inputs": "a cat", "max_length": 10})
    whisper_model = (
        "hf:openai/whisper-tiny.en",
        {
            "inputs": "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
        },
    )
    wav2vec2_model = (
        "hf:jonatasgrosman/wav2vec2-large-xlsr-53-english",
        {
            "inputs": "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
        },
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

    def test_photon_create(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abc", "-m", self.diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output

    def test_photon_create_duplicate_name(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", self.diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcd", "-m", self.diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_photon_list(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcde", "-m", self.diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(cli, ["photon", "list"])
        assert result.exit_code == 0
        assert "abcde" in result.output.lower()

    def test_photon_remove(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", "abcdef", "-m", self.diffusers_model[0]]
        )
        assert result.exit_code == 0
        assert "created" in result.output.lower()

        result = runner.invoke(cli, ["photon", "list"])
        assert result.exit_code == 0
        assert "abcdef" in result.output.lower()

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

    def _test_photon_run(self, create_first: bool, model):
        name = random_name()
        if create_first:
            runner = CliRunner()
            runner.invoke(cli, ["photon", "create", "-n", name, "-m", model[0]])

        proc, port = photon_run_server(name=name, model=model[0])
        res = requests.post(
            f"http://127.0.0.1:{port}/run",
            json=model[1],
        )
        proc.kill()

        if res.status_code != 200:
            logger.warning(f"Client: {res.status_code} {res.text}")
            logger.warning(f"Server: {proc.stdout.read().decode('utf-8')}")
            logger.warning(f"Server: {proc.stderr.read().decode('utf-8')}")
        self.assertEqual(res.status_code, 200)

    def test_photon_run(self):
        for create_first in [True, False]:
            for model in [
                self.diffusers_model,
                self.transformers_model,
                self.whisper_model,
                self.wikihow_t5_model,
            ]:
                with self.subTest(create_first=create_first, model=model[0]):
                    self._test_photon_run(create_first, model)

    def test_photon_run_path(self):
        name = random_name()

        runner = CliRunner()
        result = runner.invoke(
            cli, ["photon", "create", "-n", name, "-m", self.transformers_model[0]]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue("created" in result.output)

        path = find_photon(name)
        self.assertIsNotNone(path)

        proc, port = photon_run_server(path=path, model=self.transformers_model[0])
        res = requests.post(
            f"http://127.0.0.1:{port}/run",
            json=self.transformers_model[1],
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
