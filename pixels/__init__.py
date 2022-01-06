import json
import sys
import argparse
import asyncio
import logging
from pathlib import Path
from typing import Union

from . import api
from . import zone
from . import util


# todo: modularise to support different apis
# todo: cmpc pixels support
# todo: better rate limit handling?
# todo: legacy r/place support for kicks


__version__ = '4.0.0a'


CONFIG_FILE_PATH = Path('config.json')
IMAGES_FOLDER = Path('images')
CANVAS_LOG_PATH = Path('canvas.log')
DEBUG_LOG_PATH = Path('debug.log')
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
for logger_name in ('urllib3', 'PIL', 'discord'):
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


async def save_canvas_as_png(canvas_size, headers, path: Union[str, Path] = None):
    if path is None:
        path = CANVAS_IMAGE_PATH
    else:
        path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    canvas_bytes = await api.get_pixels(headers)
    canvas_image = util.bytes_to_image(canvas_bytes, canvas_size['width'], canvas_size['height'])
    canvas_image.save(path)


async def run_for_zone(z: zone.Zone, canvas_size: dict, headers: dict):
    """Given an img and the location of its top-left corner on the canvas, draw/repair that image."""
    log.info('Getting current canvas status')
    canvas_bytes = await api.get_pixels(headers)
    canvas = util.bytes_to_image(canvas_bytes, canvas_size['width'], canvas_size['height'])
    log.info('Got current canvas status')

    for y_index, row in enumerate(z.image_2d):
        hit_incorrect_pixel = False

        for x_index, colour in enumerate(row):
            pix_y = z.coords[1] + y_index
            pix_x = z.coords[0] + x_index
            
            coords_str_template = '({x}, {y})'
            max_coords_str = coords_str_template.format(
                x=canvas_size['height'], y=canvas_size['width']
            )
            max_coords_str_length = len(max_coords_str)
            pix_coords_str = coords_str_template.format(x=pix_x, y=pix_y)
            pix_coords_str = pix_coords_str.ljust(max_coords_str_length)

            if colour is None:
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
            if hit_incorrect_pixel and x_index % 1 == 0:
                log.info(f'Getting status of pixel at {pix_coords_str}')
                pix_status = await api.get_pixel(pix_x, pix_y, headers)
                log.info(f'Got status of pixel at {pix_coords_str}, {pix_status}')
                canvas.putpixel((pix_x, pix_y), list(pix_status))
            if canvas.getpixel((pix_x, pix_y)) == colour:
                log.info(f'Pixel at {pix_coords_str} is {colour} as intended')
            else:
                hit_incorrect_pixel = True
                log.info(f'Pixel at {pix_coords_str} will be made {colour}')
                await api.set_pixel(x=pix_x, y=pix_y, rgb=colour, headers=headers)


async def run_protections(zones_to_do: list[zone.Zone], canvas_size: dict, headers: dict):
    while True:
        try:
            for z in zones_to_do:
                log.info('working on next img'.center(100, '='))
                log.info(f"img name: {z.name}")
                log.info(f'img dimension x: {z.width}')
                log.info(f'img dimension y: {z.height}')
                log.info(f'img pixels: {z.area_opaque}')
                await run_for_zone(z, canvas_size, headers)
        except Exception as error:
            log.exception(error)


async def main_async():
    """Run the program for all imgs."""
    parser = get_parser()
    parser.parse_args()

    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    log.info('Loaded config')
    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }

    log.info('Getting canvas size')
    canvas_size = await api.get_size(headers)
    log.info(f'Canvas size: {canvas_size}')

    log.info(f'Loading zones to do from {IMAGES_FOLDER}')
    zones_to_do = zone.load_zones(IMAGES_FOLDER)
    total_area = sum(z.area_opaque for z in zones_to_do)
    log.info(f'Total area: {total_area}')
    canvas_area = canvas_size['width'] * canvas_size['height']
    total_area_percent = round(((total_area / canvas_area) * 100), 2)
    log.info(f'Total area: {total_area_percent}% of canvas')

    log.info(f'Saving current canvas as png to {CANVAS_IMAGE_PATH}')
    await save_canvas_as_png(canvas_size, headers)
    await run_protections(zones_to_do, canvas_size, headers)


def main():
    asyncio.run(main_async())


if __name__ == '__main__':
    # todo: clean keyboardinterrupt shutdown
    main()
