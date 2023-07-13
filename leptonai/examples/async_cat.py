import aiohttp

from leptonai.photon import Photon


class AsyncCat(Photon):
    requirement_dependency = ["aiohttp"]

    @Photon.handler
    async def cat(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.text()
