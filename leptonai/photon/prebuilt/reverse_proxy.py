import os
from typing import Optional

from fastapi import FastAPI, Request, Response
import httpx

from loguru import logger

from leptonai.photon import Photon
from leptonai.config import ENV_VAR_REQUIRED


class ReverseProxy(Photon):
    """
    The Lepton reverse proxy to forward requests to your own service.

    If you have a service running on your own server with IP address and port as
    xx.xx.xx.xx:yyyy, and is protected by a token "TOKEN", you can use this
    reverse proxy to forward requests to your service, by specifying the following
    environment variables: PROXY_IP=xx.xx.xx.xx, PROXY_PORT=yyyy, PROXY_DEPLOYMENT_TOKEN=TOKEN.
    """
    deployment_template = {
        "resource_shape": "cpu.small",
        "env": {
            "PROXY_DEPLOYMENT_TOKEN": "test",
            "PROXY_IP": "127.0.0.1",
            "PROXY_PORT": "8080",
        },
    }

    proxy_app: Optional[FastAPI] = None

    def create_proxy_app(self):
        if self.proxy_app is not None:
            return self.proxy_app

        logger.info("Creating mounted proxy app.")
        self.proxy_app = FastAPI()

        self.remote_ip = os.environ.get(
            "PROXY_IP", self.deployment_template["env"]["PROXY_IP"]
        )
        self.remote_port = os.environ.get(
            "PROXY_PORT", self.deployment_template["env"]["PROXY_PORT"]
        )
        self.remote_url = f"http://{self.remote_ip}:{self.remote_port}"
        self.remote_token = os.environ.get(
            "PROXY_DEPLOYMENT_TOKEN",
            self.deployment_template["env"]["PROXY_DEPLOYMENT_TOKEN"],
        )
        remote_auth = f"Bearer {self.remote_token}"

        @self.proxy_app.api_route(
            "/{path:path}", methods=["GET", "POST", "PUT", "DELETE"]
        )
        async def proxy(request: Request, path: str):
            remote_full_url = f"{self.remote_url}/{path}"
            logger.info(f"Proxying request {path} to {remote_full_url}.")
            method = request.method

            # add authentication token to request headers
            headers = dict(request.headers)
            headers["Authorization"] = remote_auth

            # Forwarding the headers and body to the server
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method,
                    remote_full_url,
                    headers=headers,
                    content=await request.body(),
                )

            # Returning the response from the server to the client
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )

        return self.proxy_app

    @Photon.handler(mount=True, path="/", use_router_if_possible=False)
    def proxy(self):
        return self.create_proxy_app()

    def openapi(self):
        def openapi():
            with httpx.Client() as client:
                resp = client.get(
                    self.remote_url + "/openapi.json",
                    headers={"Authorization": f"Bearer {self.remote_token}"},
                )
                return resp.json()

        return openapi


if __name__ == "__main__":
    ph = ReverseProxy()
    ph.launch()
