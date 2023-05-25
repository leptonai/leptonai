import os
import tempfile

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import atexit
import unittest

from loguru import logger

from lepton import photon
from lepton.config import BASE_IMAGE
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


@unittest.skipIf(not has_docker, "Docker not installed")
class TestDocker(unittest.TestCase):
    def test_common_image(self):
        client.containers.run(BASE_IMAGE, "lepton photon -h")

    def test_run_hf_photon(self):
        ph = photon.create(random_name(), "hf:gpt2")
        path = photon.save(ph)
        container_path = f"/tmp/{os.path.basename(path)}"
        image = photon.load_metadata(path)["image"]
        container = client.containers.run(
            image=image,
            command=f"lepton photon run -f {container_path}",
            volumes=[f"{path}:{container_path}"],
            detach=True,
            auto_remove=True,
            remove=True,
        )
        atexit.register(container.stop)
        for log in container.logs(stream=True):
            line = log.decode("utf-8").strip()
            logger.info(line)
            if "running" in line.lower():
                container.stop()
                break
        else:
            self.fail("Failed to start photon")


if __name__ == "__main__":
    unittest.main()
