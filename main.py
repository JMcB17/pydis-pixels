#!/usr/bin/env python

import json
import sys
import typing
import re
import time
import logging
import argparse
import asyncio
from pathlib import Path

import aiohttp
import multidict
import PIL.Image

import discord_mirror


__version__ = '3.1.0'


# modify this to change the order of priority or add/remove images
imgs = [
    'pride-whole-canvas-mask',
    'cmpc',
    'httpscmpclivetwitchtvcontrolmypc-utf-8',
    'wbub',
    'jmcb',
    'voxelfox',
    'httpsvflgg-utf-8',
    'JMcB-utf-8',
    'sqlite-lgbt',
    'pydispix',
]


CONFIG_FILE_PATH = Path('config.json')
IMGS_FOLDER = Path('imgs')
CANVAS_LOG_PATH = Path('canvas.log')
DEBUG_LOG_PATH = Path('debug.log')
CANVAS_IMAGE_PATH = Path('imgs') / 'upscale' / 'canvas.png'
WORM_COLOUR = 'ff8983'
GMTIME = False
BASE_URL = 'https://pixels.pythondiscord.com'
SET_PIXEL_URL = f'{BASE_URL}/set_pixel'
GET_SIZE_URL = f'{BASE_URL}/get_size'
GET_PIXELS_URL = f'{BASE_URL}/get_pixels'
GET_PIXEL_URL = f'{BASE_URL}/get_pixel'
BLANK_PIXEL = 'ffffff'


img_type = typing.List[typing.List[str]]


# file handler for all debug logging with timestamps
file_handler = logging.FileHandler(DEBUG_LOG_PATH, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s:' + logging.BASIC_FORMAT)
file_handler.setFormatter(file_formatter)
# stream handler for info level print-like logging
stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_formatter = logging.Formatter()
stream_handler.setFormatter(stream_formatter)
# noinspection PyArgumentList
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        file_handler,
        stream_handler,
    ]
)
# don't fill up debug.log with other loggers
for logger_name in ['urllib3', 'PIL', 'discord']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)


def get_parser() -> argparse.ArgumentParser:
    """Get this script's parser."""
    parser = argparse.ArgumentParser(
        description=f'load images and their coords from {IMGS_FOLDER} and try to create/protect them'
    )

    parser.add_argument('--version', action='version', version=__version__)
    # parser.add_argument('-g', '--gui', action='store_true', help='run a live tkinter display of the canvas')

    return parser


def three_ints_to_rgb_hex_string(rgb_ints: typing.List[int]) -> str:
    """Take a list of ints and convert it to a colour e.g. [255, 255, 255] -> ffffff."""
    rgb_hex = [hex(i) for i in rgb_ints]
    rgb_hex_strings = [str(h)[2:].rjust(2, '0') for h in rgb_hex]
    rgb_hex_string = ''.join(rgb_hex_strings)

    return rgb_hex_string


def three_bytes_to_rgb_hex_string(pixel: bytes) -> str:
    """Take three bytes and convert them to a colour."""
    rgb_ints = [b for b in pixel]
    return three_ints_to_rgb_hex_string(rgb_ints)


# mode of pil_img should be RGBA
def img_to_lists(pil_img: PIL.Image.Image) -> img_type:
    """Convert a PIL image to a 2d list of hex colour strings (None for transparent pixels)."""
    pixel_list_img = []
    for p in pil_img.getdata():
        # if alpha channel shows pixel is transparent, save None instead
        if p[3] == 0:
            pixel_list_img.append(None)
        else:
            pixel_list_img.append(three_ints_to_rgb_hex_string(p[:3]))

    dimensional_list_img = []
    for i in range(pil_img.height):
        w = pil_img.width
        dimensional_list_img.append(pixel_list_img[i*w:i*w + w])

    return dimensional_list_img


def scale_img(pil_img: PIL.Image.Image, scale: int) -> PIL.Image.Image:
    """Calculate the new size of a PIL image, resize and return it."""
    new_size = (
        pil_img.width // scale,
        pil_img.height // scale
    )
    return pil_img.resize(size=new_size, resample=PIL.Image.NEAREST)


class Zone:
    """An area of pixels on the canvas, to be maintained.

    Attrs:
        img_path -- path provided to constructor
        name -- name from filename
        scale -- scale from filename
        location -- co-ordinates on canvas of top-left corner
        width
        height
        area
        img -- a 2d list of hex colour strings, like run_for_img takes
    """
    img_name_regexp = re.compile(r'(.*),([0-9]*)x,\(([0-9]*),([0-9]*)\)')

    def __init__(self, img_path: typing.Union[str, Path]):
        """Load an image and calulcate its attributes.

        Args:
            img_path -- str or Path object to an image
        Its name should match Zone.img_name_regexp:
        name,scalex,(x,y)
        e.g.
        jmcb,10x,(75,2)
        This is used by the code.
        The image is resized and converted to a 2d list of hex colour strings.
        """
        if not isinstance(img_path, Path):
            img_path = Path(img_path)
        self.img_path = img_path

        filename = self.img_path.stem
        properties = re.match(self.img_name_regexp, filename)
        self.name = properties[1]
        self.scale = int(properties[2])
        self.location = {
            'x': int(properties[3]),
            'y': int(properties[4])
        }

        pil_img = PIL.Image.open(self.img_path)
        pil_img_rgb = pil_img.convert('RGBA')
        if self.scale != 1:
            pil_img_scaled = scale_img(pil_img_rgb, self.scale)
        else:
            pil_img_scaled = pil_img_rgb
        self.width = pil_img_scaled.width
        self.height = pil_img_scaled.height
        self.area = self.width * self.height
        self.img = img_to_lists(pil_img_scaled)

        self.area_not_transparent = self.area
        for row in self.img:
            for pixel in row:
                if pixel is None:
                    self.area_not_transparent -= 1

        logging.info(
            f'Loaded zone {self.name}\n'
            f'    width:  {self.width}\n'
            f'    height: {self.height}\n'
            f'    area:   {self.area}'
        )


def load_zones(directory: Path, img_names: list) -> typing.List[Zone]:
    """Load zones that match img_names from directory and return them."""
    zones = []

    for img in img_names:
        for file in directory.iterdir():
            if file.name.startswith(img) and file.is_file():
                zones.append(Zone(file))
                break

    return zones


def print_sleep_time(
        duration: float,
        duration_msg: str = 'sleeping for {duration} seconds',
        finish_msg: str = 'finish sleeping at {sleep_finish_time}'
):
    logging.info(duration_msg.format(duration=duration))
    sleep_finish_time_posix = time.time() + duration
    if GMTIME:
        sleep_finish_time_struct = time.gmtime(sleep_finish_time_posix)
    else:
        sleep_finish_time_struct = time.localtime(sleep_finish_time_posix)
    sleep_finish_time = time.asctime(sleep_finish_time_struct)
    logging.info(finish_msg.format(sleep_finish_time=sleep_finish_time))


async def ratelimit(headers: multidict.CIMultiDictProxy):
    """Given headers from a response, print info and sleep if needed."""
    if 'requests-remaining' in headers:
        requests_remaining = int(headers['requests-remaining'])
        logging.info(f'{requests_remaining} requests remaining')
        if not requests_remaining:
            requests_reset = float(headers['requests-reset'])
            print_sleep_time(requests_reset)
            await asyncio.sleep(requests_reset)
    else:
        cooldown_reset = float(headers['cooldown-reset'])
        logging.info('on cooldown')
        print_sleep_time(cooldown_reset)
        await asyncio.sleep(cooldown_reset)


async def head_request(url: str, headers: dict):
    async with aiohttp.ClientSession() as session:
        async with session.head(url, headers=headers) as r:
            # todo: custom logging for head requests
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
            logging.info(r_json['message'])
            await ratelimit(r.headers)


def img_bytes_to_dimensional_list(img_bytes: bytes, canvas_size: dict) -> img_type:
    canvas = []
    for y in range(canvas_size['height']):
        row = []
        for x in range(canvas_size['width']):
            index = (y * canvas_size['width'] * 3) + (x * 3)
            pixel = img_bytes[index:index + 3]
            row.append(three_bytes_to_rgb_hex_string(pixel))
        canvas.append(row)

    return canvas


def empty_canvas(canvas_size: dict) -> img_type:
    return [[BLANK_PIXEL] * canvas_size['width']] * canvas_size['height']


def empty_canvas_bytes(canvas_size: dict) -> bytes:
    return b'ffffff' * canvas_size['height'] * canvas_size['width']


async def get_pixels(canvas_size: dict, headers: dict, as_bytes: bool = False) -> typing.Union[img_type, bytes]:
    """get_pixels endpoint wrapper.

    Returns as a 2d list of hex colour strings, like an img.
    """
    await head_request(GET_PIXELS_URL, headers)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GET_PIXELS_URL,
            headers=headers
        ) as r:
            if r.status == 410:

                logging.debug('Rats! get_pixels will return a blank canvas as default.')
                print_sleep_time(
                    float(r.headers['endpoint-unlock']),
                    'endpoint will unlock in {duration} seconds',
                    'endpoint will unlock at {sleep_finish_time}'
                )
                pixels_bytes = empty_canvas_bytes(canvas_size)
            else:
                await ratelimit(r.headers)
                pixels_bytes = await r.read()

    with open(CANVAS_LOG_PATH, 'a', encoding='utf-8') as canvas_log_file:
        canvas_log_file.write(f'{time.asctime()}\n{pixels_bytes}\n')
    if as_bytes:
        return pixels_bytes

    return img_bytes_to_dimensional_list(pixels_bytes, canvas_size)


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
            if r.status == 410:
                logging.debug('Rats! get_pixel will return a black pixel as default.')
                print_sleep_time(
                    float(r.headers['endpoint-unlock']),
                    'endpoint will unlock in {duration} seconds',
                    'endpoint will unlock at {sleep_finish_time}'
                )
                return BLANK_PIXEL

            await ratelimit(r.headers)
            r_json = await r.json()

    return r_json['rgb']


async def get_size(headers: dict) -> typing.Dict[str, int]:
    """get_size endpoint wrapper."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            GET_SIZE_URL,
            headers=headers
        ) as r:
            return await r.json()


async def save_canvas_as_png(canvas_size, headers, path: typing.Union[str, Path] = None):
    if path is None:
        path = CANVAS_IMAGE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    canvas_bytes = await get_pixels(canvas_size, headers, as_bytes=True)
    canvas_pil_img = PIL.Image.frombytes(
        mode='RGB',
        size=(canvas_size['width'], canvas_size['height']),
        data=canvas_bytes
    )
    canvas_pil_img.save(path)


async def run_for_img(img: img_type, img_location: dict, canvas_size: dict, headers: dict, bot):
    """Given an img and the location of its top-left corner on the canvas, draw/repair that image."""
    logging.info('Getting current canvas status')
    canvas_bytes = await get_pixels(canvas_size, headers, as_bytes=True)
    canvas = img_bytes_to_dimensional_list(canvas_bytes, canvas_size)
    logging.info('Got current canvas status')
    if bot is not None:
        logging.info('Updating canvas mirror')
        await bot.update_mirror_from_id(canvas_bytes)

    for y_index, row in enumerate(img):
        hit_incorrect_pixel = False

        for x_index, colour in enumerate(row):
            pix_y = img_location['y'] + y_index
            pix_x = img_location['x'] + x_index

            if colour is None:
                logging.info(f'Pixel at ({pix_x}, {pix_y}) is intended to be transparent, skipping')
                continue
            # get canvas every other time
            # getting it more often means better collaboration
            # but too often is too often
            # also only do it if we've hit a zone that needs changing, to further prevent get_pixel rate limiting
            if hit_incorrect_pixel and x_index % 2 == 0:
                logging.info(f'Getting status of pixel at ({pix_x}, {pix_y})')
                canvas[pix_y][pix_x] = await get_pixel(pix_x, pix_y, headers)
                logging.info(f'Got status of pixel at ({pix_x}, {pix_y}), {canvas[pix_y][pix_x]}')
            if canvas[pix_y][pix_x] == colour:
                logging.info(f'Pixel at ({pix_x}, {pix_y}) is {colour} as intended')
            elif colour == WORM_COLOUR:
                logging.info('Oh, worm')
            else:
                hit_incorrect_pixel = True
                logging.info(f'Pixel at ({pix_x}, {pix_y}) will be made {colour}')
                await set_pixel(x=pix_x, y=pix_y, rgb=colour, headers=headers)


async def run_protections(zones_to_do: typing.List[Zone], canvas_size: dict, headers: dict, bot):
    while True:
        try:
            for zone in zones_to_do:
                img = zone.img
                img_location = zone.location

                logging.info(f"img name: {zone.name}")
                logging.info(f'img dimension x: {zone.width}')
                logging.info(f'img dimension y: {zone.height}')
                logging.info(f'img pixels: {zone.area_not_transparent}')
                await run_for_img(img, img_location, canvas_size, headers, bot)
        except Exception as error:
            logging.exception(error)


async def main():
    """Run the program for all imgs."""
    parser = get_parser()
    parser.parse_args()

    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    logging.info('Loaded config')
    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }

    logging.info('Getting canvas size')
    canvas_size = await get_size(headers)
    logging.info(f'Canvas size: {canvas_size}')

    if 'discord_mirror' in config and config['discord_mirror']['bot_token']:
        bot = discord_mirror.MirrorBot(
            channel_id=config['discord_mirror']['channel_id'], message_id=config['discord_mirror']['message_id'],
            canvas_size=canvas_size
        )
        logging.info('Running discord bot for canvas mirror')
        asyncio.create_task(bot.start(config['discord_mirror']['bot_token']))
        await bot.wait_until_ready()
    else:
        bot = None

    logging.info(f'Loading zones to do from {IMGS_FOLDER}')
    zones_to_do = load_zones(IMGS_FOLDER, imgs)
    total_area = sum(z.area_not_transparent for z in zones_to_do)
    logging.info(f'Total area: {total_area}')
    canvas_area = canvas_size['width'] * canvas_size['height']
    total_area_percent = round(((total_area / canvas_area) * 100), 2)
    logging.info(f'Total area: {total_area_percent}% of canvas')

    logging.info(f'Saving current canvas as png to {CANVAS_IMAGE_PATH}')
    await save_canvas_as_png(canvas_size, headers)
    await run_protections(zones_to_do, canvas_size, headers, bot)


if __name__ == '__main__':
    asyncio.run(main())
