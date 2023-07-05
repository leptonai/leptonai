import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

try:
    from flask import Flask
except ImportError:
    has_flask = False
else:
    has_flask = True

try:
    import gradio as gr
except ImportError:
    has_gradio = False
else:
    has_gradio = True

from io import BytesIO
import inspect
import json
from textwrap import dedent
import shutil
import subprocess
import sys
import unittest
import zipfile

from fastapi import FastAPI
from loguru import logger
import numpy as np
import requests
import torch

import leptonai
from leptonai import Client
from leptonai.photon.api import create as create_photon, load_metadata
from leptonai.photon.constants import METADATA_VCS_URL_KEY, LEPTON_DASHBOARD_URL
from leptonai.photon import Photon, HTTPException, PNGResponse
from leptonai.util import switch_cwd


from utils import random_name, photon_run_server


class CustomPhoton(Photon):
    input_example = {"x": 2.0}

    def init(self):
        self.nn = torch.nn.Linear(1, 1)

    @Photon.handler("some_path", example=input_example)
    def run(self, x: float) -> float:
        return self.nn(torch.tensor(x).reshape(1, 1)).item()

    @Photon.handler("some_path_2")
    def run2(self, x: float) -> float:
        return x * 2

    @Photon.handler("")
    def run3(self, x: float) -> float:
        return x * 3


class CustomPhotonWithCustomDeps(Photon):
    requirement_dependency = ["torch"]
    system_dependency = ["ffmpeg"]


class CustomPhotonAutoCaptureDeps(Photon):
    capture_requirement_dependency = True


test_txt = tempfile.NamedTemporaryFile(suffix=".txt")
with open(test_txt.name, "w") as f:
    for i in range(10):
        f.write(f"line {i}\n")
    f.flush()


class CustomPhotonWithCustomExtraFiles(Photon):
    extra_files = {
        "test.txt": test_txt.name,
        "a/b/c/test.txt": test_txt.name,
    }

    def init(self):
        with open("test.txt") as f:
            self.lines = f.readlines()
        with open("a/b/c/test.txt") as f:
            self.lines.extend(f.readlines())

    @Photon.handler("line")
    def run(self, n: int) -> str:
        if n >= len(self.lines):
            raise HTTPException(
                status_code=400, detail=f"n={n} exceeds total #lines ({self.lines})"
            )
        return self.lines[n]


class CustomPhotonWithPNGResponse(Photon):
    @Photon.handler()
    def img(self, content: str) -> PNGResponse:
        img_io = BytesIO()
        img_io.write(content.encode("utf-8"))
        img_io.seek(0)
        return PNGResponse(img_io)


class CustomPhotonWithMount(Photon):
    @Photon.handler(mount=True)
    def myapp(self):
        app = FastAPI()

        @app.post("/hello")
        def hello():
            return "world"

        return app

    @Photon.handler()
    def run(self):
        return "hello"


class TestPhoton(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_run(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        x = 2.0
        y1 = ph.run(x)

        xtensor = torch.tensor(x).reshape(1, 1)
        y2 = ph.nn(xtensor).item()
        self.assertEqual(y1, y2)

    def test_save_load(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        x = 2.0
        y1 = ph.run(x)

        path = ph.save()

        ph = leptonai.photon.load(path)
        y2 = ph.run(x)
        self.assertEqual(y1, y2)

    def test_run_server(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        path = ph.save()

        proc, port = photon_run_server(path=path)

        x = 2.0
        res = requests.post(
            f"http://localhost:{port}/some_path",
            json={"x": x},
        )
        self.assertEqual(res.status_code, 200)
        res = requests.post(
            f"http://localhost:{port}",
            json={"x": x},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 6.0)
        proc.kill()

    def test_client(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        x = 2.0
        y1 = ph.run(x)
        path = ph.save()

        proc, port = photon_run_server(path=path)
        url = f"http://localhost:{port}"

        client = Client(url)
        y2 = client.some_path(x=x)
        self.assertEqual(y1, y2)
        try:
            client.some_path_does_not_exist(x=x)
        except AttributeError:
            pass
        else:
            self.fail("AttributeError not raised")
        proc.kill()

    def test_ph_cli(self):
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            f.write(dedent("""
from leptonai.photon import Photon


class Counter(Photon):
    def init(self):
        self.counter = 0

    @Photon.handler("add")
    def add(self, x: int) -> int:
        self.counter += x
        return self.counter

    @Photon.handler("sub")
    def sub(self, x: int) -> int:
        self.counter -= x
        return self.counter
""").encode("utf-8"))
            f.flush()
            for model in [f"py:{f.name}:Counter", f"{f.name}:Counter"]:
                proc, port = photon_run_server(name="counter", model=model)
                res = requests.post(
                    f"http://127.0.0.1:{port}/add",
                    json={"x": 1},
                )
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json(), 1)

                res = requests.post(
                    f"http://127.0.0.1:{port}/add",
                    json={"x": 1},
                )
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json(), 2)

                res = requests.post(
                    f"http://127.0.0.1:{port}/sub",
                    json={"x": 2},
                )
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json(), 0)
                proc.kill()

    def test_photon_file_metadata(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        path = ph.save()
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as metadata_file:
                metadata = json.load(metadata_file)
        self.assertEqual(metadata["name"], name)
        self.assertEqual(metadata["model"], "CustomPhoton")
        self.assertTrue("image" in metadata)
        self.assertTrue("args" in metadata)

        # check for openapi schema
        self.assertTrue("openapi_schema" in metadata)
        self.assertTrue("/some_path" in metadata["openapi_schema"]["paths"])
        # check for annotated example
        self.assertEqual(
            metadata["openapi_schema"]["paths"]["/some_path"]["post"]["requestBody"][
                "content"
            ]["application/json"]["example"],
            CustomPhoton.input_example,
        )
        # handler without specifying example should not have 'example' in metadata
        with self.assertRaises(KeyError) as raises:
            metadata["openapi_schema"]["paths"]["/some_path_2"]["post"]["requestBody"][
                "content"
            ]["application/json"]["example"]
        self.assertEqual(raises.exception.args[0], "example")

        self.assertEqual(len(metadata["requirement_dependency"]), 0)

    def test_capture_dependency(self):
        name = random_name()
        ph = CustomPhotonAutoCaptureDeps(name=name)
        path = ph.save()
        metadata = load_metadata(path)
        self.assertGreater(len(metadata["requirement_dependency"]), 0)

    def test_custom_dependency(self):
        name = random_name()
        ph = CustomPhotonWithCustomDeps(name=name)
        path = ph.save()
        metadata = load_metadata(path)
        self.assertEqual(
            metadata["requirement_dependency"],
            CustomPhotonWithCustomDeps.requirement_dependency,
        )
        self.assertEqual(
            metadata["system_dependency"],
            CustomPhotonWithCustomDeps.system_dependency,
        )

    def test_metrics(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        path = ph.save()

        proc, port = photon_run_server(path=path)

        for x in range(5):
            res = requests.post(
                f"http://127.0.0.1:{port}/some_path",
                json={"x": float(x)},
            )
            self.assertEqual(res.status_code, 200)
        res = requests.get(f"http://127.0.0.1:{port}/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertRegex(
            res.text, r'http_request_duration_seconds_count{handler="/some_path"}'
        )
        self.assertRegex(
            res.text,
            r'http_request_duration_seconds_bucket{handler="/some_path",le="0.01"}',
        )
        self.assertRegex(
            res.text,
            r'http_request_duration_seconds_bucket{handler="/some_path",le="0.78"}',
        )
        self.assertRegex(
            res.text,
            r'http_request_duration_seconds_bucket{handler="/some_path",le="1.1"}',
        )
        self.assertRegex(
            res.text,
            r'http_request_duration_seconds_bucket{handler="/some_path",le="2.3"}',
        )
        proc.kill()

    def test_vec_db_examples(self):
        name = random_name()

        vec_db_path = os.path.join(
            os.path.dirname(leptonai.__file__), "examples", "vec_db.py"
        )
        with tempfile.NamedTemporaryFile(suffix=".py", dir=tmpdir) as f, open(
            vec_db_path, "rb"
        ) as vec_db_file:
            f.write(vec_db_file.read())
            f.flush()
            proc, port = photon_run_server(name="vec-db", model=f"py:{f.name}:VecDB")

        dim = 2
        name = "two"

        # create collection
        res = requests.post(
            f"http://127.0.0.1:{port}/create_collection",
            json={"name": name, "dim": dim},
        )
        self.assertEqual(res.status_code, 200)

        # list collections
        # TODO: this should be get, not post
        res = requests.post(f"http://127.0.0.1:{port}/list_collections", json={})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [[name, dim]])

        # create second collection, list collections, remove it and list collections again
        name2 = random_name()
        res = requests.post(
            f"http://127.0.0.1:{port}/create_collection",
            json={"name": name2, "dim": dim},
        )
        self.assertEqual(res.status_code, 200)
        res = requests.post(f"http://127.0.0.1:{port}/list_collections", json={})
        self.assertEqual(res.status_code, 200)
        self.assertTrue([name2, dim] in res.json())
        res = requests.post(
            f"http://127.0.0.1:{port}/remove_collection", json={"name": name2}
        )
        self.assertEqual(res.status_code, 200)
        res = requests.post(f"http://127.0.0.1:{port}/list_collections", json={})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [[name, dim]])

        # insert
        count = 10
        embeddings = []
        for i in range(count):
            vector = np.random.rand(dim).tolist()
            text = f"text_{i}"
            doc_id = f"doc_id_{i}"
            embeddings.append({"doc_id": doc_id, "text": text, "vector": vector})
        res = requests.post(
            f"http://127.0.0.1:{port}/add",
            json={"name": name, "embeddings": embeddings},
        )
        self.assertEqual(res.status_code, 200)
        res = requests.post(f"http://127.0.0.1:{port}/count", json={"name": name})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), count)

        # get
        res = requests.post(
            f"http://127.0.0.1:{port}/get",
            json={"name": name, "doc_ids": ["doc_id_0", "doc_id_2"]},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)
        self.assertTrue(
            np.allclose(
                [r["vector"] for r in res.json()],
                [embeddings[0]["vector"], embeddings[2]["vector"]],
            )
        )

        # search
        k = 3
        res = requests.post(
            f"http://127.0.0.1:{port}/search",
            json={"name": name, "vector": embeddings[0]["vector"], "k": k},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), k)
        self.assertEqual(res.json()[0]["doc_id"], embeddings[0]["doc_id"])

        # delete
        res = requests.post(
            f"http://127.0.0.1:{port}/delete",
            json={"name": name, "doc_ids": [embeddings[0]["doc_id"]]},
        )
        self.assertEqual(res.status_code, 200)
        res = requests.post(f"http://127.0.0.1:{port}/count", json={"name": name})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), count - 1)

        proc.kill()

    def test_extra_files(self):
        name = random_name()
        ph = CustomPhotonWithCustomExtraFiles(name=name)
        path = ph.save()

        proc, port = photon_run_server(path=path)
        res = requests.post(
            f"http://127.0.0.1:{port}/line",
            json={"n": 1},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), "line 1\n")
        proc.kill()

    def test_git_remote(self):
        # setup a git repo with custom.py
        git_proj = tempfile.mkdtemp(dir=tmpdir)
        with switch_cwd(git_proj):
            subprocess.check_call(["git", "init"])
            subprocess.check_call(["git", "checkout", "-b", "main"])
            subprocess.check_call(["git", "config", "--local", "user.email", "a@b.c"])
            subprocess.check_call(["git", "config", "--local", "user.name", "abc"])
            custom_py = os.path.join("d1", "d2", "custom.py")
            os.makedirs(os.path.dirname(custom_py))
            with open(custom_py, "w") as f:
                f.write(dedent(f"""
import torch
from leptonai.photon import Photon

{inspect.getsource(CustomPhoton)}
"""))
            subprocess.check_call(["git", "add", custom_py])
            subprocess.check_call(["git", "commit", "-m", "add custom ph"])

        for model in [
            f"py:file://{git_proj}:{custom_py}:CustomPhoton",
            f"file://{git_proj}:{custom_py}:CustomPhoton",
        ]:
            name = random_name()
            proc, port = photon_run_server(name=name, model=model)
            res = requests.post(
                f"http://127.0.0.1:{port}/some_path",
                json={"x": 1.0},
            )
            proc.kill()
            self.assertEqual(res.status_code, 200)

        # test environment variable substitution in vcs url
        with switch_cwd(git_proj):
            custom_py = os.path.join("d1", "d2", "custom.py")
            custom_2_py = os.path.join("d1", "d2", "custom2.py")
            shutil.copyfile(custom_py, custom_2_py)
            subprocess.check_call(["git", "add", custom_2_py])
            subprocess.check_call(["git", "commit", "-m", "add custom ph 2"])

        try:
            name = random_name()
            os.environ["GIT_PROJ_URL"] = git_proj
            model = "py:file://${GIT_PROJ_URL}:" + custom_2_py + ":CustomPhoton"
            photon = create_photon(name=name, model=model)
            path = photon.save()
            metadata = load_metadata(path)
            saved_url = metadata[METADATA_VCS_URL_KEY]
            self.assertTrue("${GIT_PROJ_URL}" in saved_url)
            self.assertFalse(git_proj in saved_url)
            proc, port = photon_run_server(path=path)
            res = requests.post(
                f"http://127.0.0.1:{port}/some_path",
                json={"x": 1.0},
            )
            proc.kill()
            self.assertEqual(res.status_code, 200)
        finally:
            os.environ.pop("GIT_PROJ_URL")

        # test github user & token autofill from environment variables
        if not os.environ.get("GITHUB_USER") or not os.environ.get("GITHUB_TOKEN"):
            logger.debug(
                "Skip github user & token autofill test because env vars GITHUB_USER"
                " and GITHUB_TOKEN not set"
            )
            return
        name = random_name()
        model = "py:github.com/leptonai/examples:Counter/counter.py:Counter"
        photon = create_photon(name=name, model=model)
        path = photon.save()
        proc, port = photon_run_server(path=path)
        res = requests.post(
            f"http://127.0.0.1:{port}/add",
            json={"x": 1.0},
        )
        proc.kill()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), 1.0)

    def test_media_response(self):
        name = random_name()
        ph = CustomPhotonWithPNGResponse(name=name)
        path = ph.save()

        proc, port = photon_run_server(path=path)
        res = requests.post(
            f"http://127.0.0.1:{port}/img",
            json={"content": "invalid image"},
        )
        proc.kill()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "image/png")

    def test_allow_dashboard_cors(self):
        name = random_name()
        ph = CustomPhoton(name=name)
        path = ph.save()

        proc, port = photon_run_server(path=path)
        res = requests.post(
            f"http://127.0.0.1:{port}",
            json={"x": 1.0},
            headers={"Origin": LEPTON_DASHBOARD_URL},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers["Access-Control-Allow-Origin"], LEPTON_DASHBOARD_URL
        )

        res = requests.post(
            f"http://127.0.0.1:{port}",
            json={"x": 1.0},
            headers={"Origin": "https://some_other_url.com"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse("Access-Control-Allow-Origin" in res.headers)
        proc.kill()

    def test_mount_fastapi(self):
        ph = CustomPhotonWithMount(name=random_name())
        path = ph.save()
        proc, port = photon_run_server(path=path)
        res = requests.post(
            f"http://127.0.0.1:{port}/myapp/hello",
            json={},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            "world",
        )
        res = requests.post(
            f"http://127.0.0.1:{port}/run",
            json={},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            "hello",
        )
        proc.kill()

    @unittest.skipIf(not has_flask, "flask not installed")
    def test_mount_flask(self):
        class FlaskPhoton(Photon):
            @Photon.handler("", mount=True)
            def flask_app(self):
                flask_app = Flask(__name__)

                @flask_app.get("/run")
                def hello():
                    return "hello from flask"

                return flask_app

        ph = FlaskPhoton(name=random_name())
        path = ph.save()
        proc, port = photon_run_server(path=path)
        res = requests.get(f"http://127.0.0.1:{port}/run")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "hello from flask")
        proc.kill()

    @unittest.skipIf(not has_gradio, "gradio not installed")
    def test_mount_gradio(self):
        def greet(name):
            return "Hello " + name + "!"

        class GradioPhoton(Photon):
            @Photon.handler("ui", mount=True)
            def gradio_app(self):
                app = gr.Interface(fn=greet, inputs="text", outputs="text")
                return app

        ph = GradioPhoton(name=random_name())
        path = ph.save()
        proc, port = photon_run_server(path=path)
        res = requests.get(f"http://127.0.0.1:{port}/ui")
        self.assertEqual(res.status_code, 200)

    def test_dynamic_global_variable_warnings(self):
        class TestPhoton(Photon):
            @Photon.handler("run")
            def run(self):
                return os.path.abspath(__file__)

        ph = TestPhoton(name=random_name())
        with self.assertWarns(UserWarning):
            path = ph.save()
        # still works, just warn during photon creation
        proc, port = photon_run_server(path=path)
        res = requests.post(f"http://127.0.0.1:{port}/run", json={})
        self.assertEqual(res.status_code, 200)
        proc.kill()


if __name__ == "__main__":
    unittest.main()
