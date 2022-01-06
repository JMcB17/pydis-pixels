import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Union

from . import zone
from . import util
from .api import APIBase
from .api import cmpc


# todo: better rate limit handling?
# todo: legacy r/place support for kicks
# todo: try adding tk display again? might kill me


__version__ = '4.0.0b'


CONFIG_FILE_PATH = Path('config.json')
CANVAS_LOG_PATH = Path('canvas.log')
DEBUG_LOG_PATH = Path('debug.log')
IMAGES_FOLDER = Path('images')
CANVAS_IMAGE_PATH = IMAGES_FOLDER / 'ignore' / 'canvas.png'


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
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        file_handler,
        stream_handler,
    ]
)
# don't fill up debug.log with other loggers
for logger_name in ('asyncio', 'urllib3', 'PIL',):
    logging.getLogger(logger_name).setLevel(logging.ERROR)
log = logging.getLogger(__name__)


def get_parser() -> argparse.ArgumentParser:
    """Get this script's parser."""
    parser = argparse.ArgumentParser(
        description=f'load images and their coords from {IMAGES_FOLDER} and try to create/protect them'
    )

    parser.add_argument('--version', action='version', version=__version__)
    # parser.add_argument('-g', '--gui', action='store_true', help='run a live tkinter display of the canvas')

    return parser


async def save_canvas_as_png(api_instance: APIBase, path: Union[str, Path] = None):
    if path is None:
        path = CANVAS_IMAGE_PATH
    else:
        path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    canvas = await api_instance.get_pixels()
    canvas.save(path)


def pad_coords_str(x: int, y: int, max_x: int, max_y: int, template: str = '({x}, {y})') -> str:
    max_coords_str = template.format(x=max_x, y=max_y)
    max_coords_str_length = len(max_coords_str)
    coords_str = template.format(x=x, y=y)
    coords_str_padded = coords_str.ljust(max_coords_str_length)
    return coords_str_padded


async def run_for_zone(z: zone.Zone, api_instance: APIBase):
    """Given an img and the location of its top-left corner on the canvas, draw/repair that image."""
    log.info('Getting current canvas status')
    canvas = await api_instance.get_pixels()
    log.info('Got current canvas status')

    for index_y in range(z.image.height):
        hit_incorrect_pixel = False

        for index_x in range(z.image.width):
            pix_x = z.coords[0] + index_x
            pix_y = z.coords[1] + index_y
            pix_coords_str = pad_coords_str(pix_x, pix_y, canvas.width, canvas.height)

            colour = z.image.getpixel((pix_x, pix_y))

            if not colour[3]:
                log.info(f'Pixel at {pix_coords_str} is intended to be transparent, skipping')
                continue

            try:
                canvas.getpixel((pix_x, pix_y))
            except IndexError:
                log.error(f'Pixel at {pix_coords_str} is outside of the canvas')
            # get canvas every other time
            # getting it more often means better collaboration
            # but too often is too often
            # also only do it if we've hit a zone that needs changing, to further prevent get_pixel rate limiting
            if hit_incorrect_pixel and index_x % 1 == 0:
                log.info(f'Getting status of pixel at {pix_coords_str}')
                pix_status = await api_instance.get_pixel(pix_x, pix_y)
                log.info(f'Got status of pixel at {pix_coords_str}, {pix_status}')
                canvas.putpixel((pix_x, pix_y), list(pix_status))
            if canvas.getpixel((pix_x, pix_y)) == colour:
                log.info(f'Pixel at {pix_coords_str} is {colour} as intended')
            else:
                hit_incorrect_pixel = True
                log.info(f'Pixel at {pix_coords_str} will be made {colour}')
                await api_instance.set_pixel(x=pix_x, y=pix_y, colour=colour)


async def run_protections(zones_to_do: list[zone.Zone], api_instance: APIBase):
    while True:
        try:
            for z in zones_to_do:
                log.info(' working on next img '.center(100, '='))
                log.info(f"img name: {z.name}")
                log.info(f'img dimension x: {z.width}')
                log.info(f'img dimension y: {z.height}')
                log.info(f'img pixels: {z.area_opaque}')
                await run_for_zone(z, api_instance)
        except Exception as error:
            log.exception(error)


async def run(api_instance: APIBase):
    log.info('Getting canvas size')
    canvas_size = await api_instance.get_size()
    log.info(f'Canvas size: {canvas_size}')

    log.info(f'Loading zones to do from {IMAGES_FOLDER}')
    zones_to_do = zone.load_zones(IMAGES_FOLDER)
    total_area = sum(z.area_opaque for z in zones_to_do)
    log.info(f'Total area: {total_area}')
    canvas_area = canvas_size['width'] * canvas_size['height']
    total_area_percent = round(((total_area / canvas_area) * 100), 2)
    log.info(f'Total area: {total_area_percent}% of canvas')

    log.info(f'Saving current canvas as png to {CANVAS_IMAGE_PATH}')
    await save_canvas_as_png(api_instance)
    await run_protections(zones_to_do, api_instance)


def main():
    parser = get_parser()
    parser.parse_args()

    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    log.info('Loaded config')

    api_instance = cmpc.APICMPC(token=config['token'], username=config['username'])
    try:
        api_instance.loop.run_until_complete(run(api_instance))
    except KeyboardInterrupt:
        log.info('Stopping.')
        api_instance.loop.run_until_complete(api_instance.close())


if __name__ == '__main__':
    main()
