#!/usr/bin/env python

import json
import time
import typing
import re
from pathlib import Path

import requests
import PIL.Image


__version__ = '2.0.0'


CONFIG_FILE_PATH = Path('config.json')
IMGS_FOLDER = Path('imgs')
BASE_URL = 'https://pixels.pythondiscord.com'
SET_URL = f'{BASE_URL}/set_pixel'
GET_SIZE_URL = f'{BASE_URL}/get_size'
GET_PIXELS_URL = f'{BASE_URL}/get_pixels'
STARTUP_DELAY = 120


def three_ints_to_rgb_hex_string(rgb_ints: typing.List[int]) -> str:
    rgb_hex = [hex(i) for i in rgb_ints]
    rgb_hex_strings = [str(h)[2:] for h in rgb_hex]
    rgb_hex_string = ''.join(rgb_hex_strings)

    return rgb_hex_string


def three_bytes_to_rgb_hex_string(pixel: bytes) -> str:
    rgb_ints = [b for b in pixel]
    return three_ints_to_rgb_hex_string(rgb_ints)


def img_to_lists(pil_img: PIL.Image.Image) -> typing.List[typing.List[str]]:
    pixel_list_img = [three_ints_to_rgb_hex_string(p) for p in pil_img.getdata()]

    dimensional_list_img = []
    for i in range(pil_img.height):
        w = pil_img.width
        dimensional_list_img.append(pixel_list_img[i*w:i*w + w])

    return dimensional_list_img


def scale_img(pil_img: PIL.Image.Image, scale: int) -> PIL.Image.Image:
    new_size = (
        pil_img.width // scale,
        pil_img.height // scale
    )
    return pil_img.resize(size=new_size, resample=PIL.Image.NEAREST)


class Zone:
    """An area of pixels on the canvas, to be maintained."""
    # name,scalex,(x,y)
    # e.g.
    # jmcb,10x,(75,2)
    img_name_regexp = re.compile(r'(.*),([0-9]*)x,\(([0-9]*),([0-9]*)\)')

    def __init__(self, img_path: typing.Union[str, Path]):
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
        pil_img_rgb = pil_img.convert('RGB')
        if self.scale != 1:
            pil_img_scaled = scale_img(pil_img_rgb, self.scale)
        else:
            pil_img_scaled = pil_img_rgb
        self.img = img_to_lists(pil_img_scaled)

        print(f'Loaded zone {self.name}')
        # todo: add more logging, and total canvas coverage in load_zones


def load_zones(directory: Path):
    zones = []
    for file in directory.iterdir():
        if file.is_file():
            zones.append(Zone(file))

    return zones


def ratelimit(headers):
    if 'requests-remaining' in headers:
        requests_remaining = int(headers['requests-remaining'])
        print(f'{requests_remaining} requests remaining')
        if not requests_remaining:
            requests_reset = int(headers['requests-reset'])
            print(f'sleeping for {requests_reset} seconds')
            time.sleep(requests_reset)
    else:
        cooldown_reset = int(headers['cooldown-reset'])
        print(f'on cooldown\nsleeping for {cooldown_reset} seconds')
        time.sleep(cooldown_reset)


def set_pixel(x: int, y: int, rgb: str, headers: dict):
    payload = {
        'x': x,
        'y': y,
        'rgb': rgb,
    }
    r = requests.post(
        SET_URL,
        json=payload,
        headers=headers
    )
    print(r.json()['message'])

    ratelimit(r.headers)


def get_pixels(canvas_size: dict, headers: dict):
    r = requests.get(
        GET_PIXELS_URL,
        headers=headers
    )
    ratelimit(r.headers)

    pixels_bytes = r.content
    # todo: log to a file
    # print(pixels_bytes)
    # print(pixels_bytes.decode(encoding='utf-8', errors='ignore'))
    canvas = []
    for y in range(canvas_size['height'] + 1):
        row = []
        for x in range(canvas_size['width'] + 1):
            index = (y * canvas_size['width'] * 3) + (x * 3)
            pixel = pixels_bytes[index:index+3]
            row.append(three_bytes_to_rgb_hex_string(pixel))
        canvas.append(row)

    return canvas


def get_size(headers: dict):
    r = requests.get(
        GET_SIZE_URL,
        headers=headers
    )
    ratelimit(r.headers)
    return r.json()


def run_for_img(img, img_location, headers):
    for y_index, row in enumerate(img):
        print('Getting current canvas status')
        canvas_size = get_size(headers)
        canvas = get_pixels(canvas_size, headers)
        print('Got current canvas status')

        for x_index, colour in enumerate(row):
            pix_y = img_location['y'] + y_index
            pix_x = img_location['x'] + x_index

            if canvas[pix_y][pix_x] == colour:
                print(f'Pixel at ({pix_x}, {pix_y}) is {colour} as intended')
                continue
            else:
                print(f'Pixel at ({pix_x}, {pix_y}) will be made {colour}')
                set_pixel(x=pix_x, y=pix_y, rgb=colour, headers=headers)


def main():
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    print('Loaded config')

    print(f'Loading zones to do from {IMGS_FOLDER}')
    zones_to_do = load_zones(IMGS_FOLDER)

    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }

    print(f'sleeping for {STARTUP_DELAY} seconds')
    time.sleep(STARTUP_DELAY)
    while True:
        for zone in zones_to_do:
            img = zone.img
            img_location = zone.location

            print(f"img name: {zone.name}")
            print(f'img dimension x: {len(img[0])}')
            print(f'img dimension y: {len(img)}')
            print(f'img pixels: {len(img[0]) * len(img)}')
            run_for_img(img, img_location, headers)


if __name__ == '__main__':
    main()
