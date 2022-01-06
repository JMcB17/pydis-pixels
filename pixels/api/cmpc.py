import asyncio
import base64

from .. import util
from ._base import APIBase, Pixel


# todo: keepalive stuff?
# todo: rate limits


class APICMPC(APIBase):
    base_url = 'https://pixels.cmpc.live/'
    endpoint_set_pixel = base_url + 'set'
    endpoint_get_pixels = base_url + 'fetch'
    endpoint_auth = base_url + 'auth'
    endpoint_stayalive = base_url + 'stayalive'

    stayalive_interval_ms = 10000
    stayalive_interval_seconds = stayalive_interval_ms // 1000

    def __init__(self, username: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.username = username
        self.subscriber = False
        self.moderator = False

    async def open(self):
        await super().open()
        await self.session.post(self.endpoint_auth, headers=self.headers)
        self.loop.create_task(self.stayalive(), name='stayalive')

    async def close(self):
        await super().close()
        self.loop.stop()

    async def stayalive(self):
        while True:
            await asyncio.sleep(self.stayalive_interval_seconds)
            await self.session.post(self.endpoint_stayalive, headers=self.headers)

    async def get_pixels(self) -> bytes:
        async with self.session.get(
            url=self.endpoint_get_pixels,
            headers=self.headers
        ) as response:
            dataurl = await response.text()

        image_bytes = base64.b64decode(dataurl, validate=True)
        return image_bytes

    async def set_pixel(self, x: int, y: int, colour: Pixel):
        payload = {
            'Username': self.username,
            'Substatus': self.subscriber,
            'X': x,
            'Y': x,
            'Color': util.rgb_to_hex(colour),
        }
        return await self.session.post(
            self.endpoint_set_pixel,
            headers=self.headers,
            json=payload
        )
