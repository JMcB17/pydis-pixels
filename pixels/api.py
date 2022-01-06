import asyncio
import logging
import time

import aiohttp
from multidict import CIMultiDictProxy


log = logging.getLogger(__name__)


BASE_URL = 'https://pixels.pythondiscord.com'
SET_PIXEL_URL = f'{BASE_URL}/set_pixel'
GET_SIZE_URL = f'{BASE_URL}/get_size'
GET_PIXELS_URL = f'{BASE_URL}/get_pixels'
GET_PIXEL_URL = f'{BASE_URL}/get_pixel'


def print_sleep_time(
        duration: float,
        duration_msg: str = 'sleeping for {duration} seconds',
        finish_msg: str = 'finish sleeping at {sleep_finish_time}'
):
    log.info(duration_msg.format(duration=duration))
    sleep_finish_time_posix = time.time() + duration
    sleep_finish_time_struct = time.localtime(sleep_finish_time_posix)
    sleep_finish_time = time.asctime(sleep_finish_time_struct)
    log.info(finish_msg.format(sleep_finish_time=sleep_finish_time))


async def ratelimit(headers: CIMultiDictProxy):
    """Given headers from a response, print info and sleep if needed."""
    if 'requests-remaining' in headers:
        requests_remaining = int(headers['requests-remaining'])
        log.info(f'{requests_remaining} requests remaining')
        if not requests_remaining:
            requests_reset = float(headers['requests-reset'])
            print_sleep_time(requests_reset)
            await asyncio.sleep(requests_reset)
    else:
        cooldown_reset = float(headers['cooldown-reset'])
        log.info('on cooldown')
        print_sleep_time(cooldown_reset)
        await asyncio.sleep(cooldown_reset)


async def head_request(url: str, headers: dict):
    async with aiohttp.ClientSession() as session:
        async with session.head(url, headers=headers) as r:
            if r.ok:
                await ratelimit(r.headers)


async def set_pixel(x: int, y: int, rgb: str, headers: dict):
    """set_pixel endpoint wrapper."""
    await head_request(SET_PIXEL_URL, headers)
    payload = {
        'x': x,
        'y': y,
        'rgb': rgb,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            SET_PIXEL_URL,
            json=payload,
            headers=headers
        ) as r:
            r_json = await r.json()
            log.info(r_json['message'])
            if r.status == 503:
                log.error('Failed to write pixel')
            else:
                await ratelimit(r.headers)


async def get_pixels(headers: dict) -> bytes:
    """get_pixels endpoint wrapper.

    Returns as a 2d list of hex colour strings, like an img.
    """
    await head_request(GET_PIXELS_URL, headers)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GET_PIXELS_URL,
            headers=headers
        ) as r:
            await ratelimit(r.headers)
            pixels_bytes = await r.read()

    return pixels_bytes


async def get_pixel(x: int, y: int, headers: dict) -> str:
    """get_pixel endpoint wrapper."""
    await head_request(GET_PIXEL_URL, headers)
    params = {
        'x': x,
        'y': y
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GET_PIXEL_URL,
            params=params,
            headers=headers
        ) as r:
            await ratelimit(r.headers)
            r_json = await r.json()

    return r_json['rgb']


async def get_size(headers: dict) -> dict[str, int]:
    """get_size endpoint wrapper."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GET_SIZE_URL,
            headers=headers
        ) as r:
            return await r.json()
