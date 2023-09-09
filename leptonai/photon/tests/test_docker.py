import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from loguru import logger

from leptonai import photon
from leptonai.config import BASE_IMAGE
from utils import random_name

try:
    import docker
except ImportError:
    has_docker = False
else:
    has_docker = True

if has_docker:
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        logger.warning(f"Failed to connect to docker: {e}")
        has_docker = False


def _resolve_image(image):
    if image.startswith("default/lepton"):
        return image.replace(
            "default/lepton", "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton"
        )
    return image


@unittest.skipIf(not has_docker, "Docker not installed")
class TestDocker(unittest.TestCase):
    def test_common_image(self):
        client.containers.run(_resolve_image(BASE_IMAGE), "lep photon -h")

    def _run_photon(self, path):
        container_path = f"/tmp/{os.path.basename(path)}"
        image = photon.load_metadata(path)["image"]
        container = client.containers.run(
            image=_resolve_image(image),
            command=f"lep photon run -f {container_path}",
            volumes=[f"{path}:{container_path}"],
            detach=True,
            auto_remove=True,
            remove=True,
        )
        for log in container.logs(stream=True):
            line = log.decode("utf-8").strip()
            logger.info(line)
            if "running" in line.lower():
                container.stop()
                break
        else:
            self.fail("Failed to start photon")

    def test_run_hf_photon(self):
        ph = photon.create(random_name(), "hf:gpt2")
        path = photon.save(ph)
        self._run_photon(path)

    def test_run_local_photon(self):
        ph = photon.create(
            random_name(),
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "examples/async_cat.py",
            ),
        )
        path = photon.save(ph)
        self._run_photon(path)

    @unittest.skipIf(
        not (os.environ.get("GITHUB_USER") and os.environ.get("GITHUB_TOKEN")),
        "No github credentials",
    )
    def test_run_remote_git_photon(self):
        ph = photon.create(
            random_name(),
            "https://github.com/leptonai/leptonai-sdk.git@a7a6e58#subdirectory=leptonai/examples:async_cat.py",
        )
        path = photon.save(ph)
        self._run_photon(path)


if __name__ == "__main__":
    unittest.main()
