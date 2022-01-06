import asyncio
import logging
import time
from typing import Optional

import aiohttp

from .. import util


Pixel = list[int]


class APIBase:
    canvas_size_assumed = {
        'width': 0,
        'height': 0,
    }

    def __init__(self, token: str = ''):
        self.token = token
        self.headers = {
            "Authorization": 'Bearer ' + self.token,
        }

        self.loop = asyncio.get_event_loop()

        self.log = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.loop.run_until_complete(self.open())

    async def open(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    def print_sleep_time(
            self,
            duration: float,
            duration_msg: str = 'sleeping for {duration} seconds',
            finish_msg: str = 'finish sleeping at {sleep_finish_time}'
    ):
        self.log.info(duration_msg.format(duration=duration))
        sleep_finish_time_posix = time.time() + duration
        sleep_finish_time_struct = time.localtime(sleep_finish_time_posix)
        sleep_finish_time = time.asctime(sleep_finish_time_struct)
        self.log.info(finish_msg.format(sleep_finish_time=sleep_finish_time))

    async def set_pixel(self, x: int, y: int, colour: Pixel):
        raise NotImplementedError

    async def get_pixel(self, x: int, y: int) -> Pixel:
        canvas_bytes = await self.get_pixels()
        canvas_size = await self.get_size()
        canvas = util.bytes_to_image(canvas_bytes, canvas_size['width'], canvas_size['height'])

        return canvas.getpixel((x, y))

    async def get_pixels(self) -> bytes:
        raise NotImplementedError

    async def get_size(self) -> dict[str, int]:
        return self.canvas_size_assumed
