#!/usr/bin/env python

import json
import time
import typing
from pathlib import Path

import requests
import PIL.Image


__version__ = '1.0.0'


CONFIG_FILE_PATH = Path('config.json')
BASE_URL = 'https://pixels.pythondiscord.com'
SET_URL = f'{BASE_URL}/set_pixel'
GET_SIZE_URL = f'{BASE_URL}/get_size'
GET_PIXELS_URL = f'{BASE_URL}/get_pixels'
CANVAS_SIZE = {
    'width': 160,
    'height': 90,
}
STARTUP_DELAY = 120


# COLOURS
# noinspection SpellCheckingInspection
target_colour = '1dbfff'
blank_colour = 'ffffff'
# noinspection SpellCheckingInspection
divider_blue = '7ecde9'
cmpc_blue = '0006ff'
cmpc_red = 'ff0000'
colours = {
    0: blank_colour,
    1: target_colour,
    2: cmpc_blue,
    3: cmpc_red,
    4: divider_blue,
}


# IMAGES
# JMCB
img_jmcb = [
    [1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 4],
    [0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 4],
    [1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 4],
]
# CMPC
# 14x3
img_cmpc = [
    [2, 2, 0, 2, 2, 0, 2, 3, 0, 3, 3, 0, 3, 3],
    [2, 0, 0, 2, 0, 3, 0, 3, 0, 3, 3, 0, 3, 0],
    [2, 2, 0, 2, 0, 0, 0, 3, 0, 3, 0, 0, 3, 3],
]


# ZONES (img + location pairs)
jmcb_zone = {
    'name': 'JMCB',
    'img': img_jmcb,
    'img_location': {
        'x': 75,
        'y': 2
    }
}
cmpc_zone = {
    'name': 'CMPC',
    'img': img_cmpc,
    'img_location': {
        'x': 13,
        'y': 42
    }
}

# MODIFY THIS
zones_to_do = [
    cmpc_zone,
    jmcb_zone,
]


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


def three_ints_to_rgb_hex_string(rgb_ints: typing.List[int]) -> str:
    rgb_hex = [hex(i) for i in rgb_ints]
    rgb_hex_strings = [str(h)[2:] for h in rgb_hex]
    rgb_hex_string = ''.join(rgb_hex_strings)

    return rgb_hex_string


def three_bytes_to_rgb_hex_string(pixel: bytes) -> str:
    rgb_ints = [b for b in pixel]
    return three_ints_to_rgb_hex_string(rgb_ints)


def img_to_lists(img_path: typing.Union[str, Path]) -> typing.List[typing.List[str]]:
    pil_img = PIL.Image.open(img_path)
    pixel_list_img = [three_ints_to_rgb_hex_string(p) for p in pil_img.getdata()]

    dimensional_list_img = []
    for i in range(pil_img.height):
        w = pil_img.width
        dimensional_list_img.append(pixel_list_img[i*w:i*w + w])

    return dimensional_list_img


def get_pixels(headers: dict):
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
    for y in range(CANVAS_SIZE['height']+1):
        row = []
        for x in range(CANVAS_SIZE['width']+1):
            index = (y * CANVAS_SIZE['width'] * 3) + (x * 3)
            pixel = pixels_bytes[index:index+3]
            row.append(three_bytes_to_rgb_hex_string(pixel))
        canvas.append(row)

    return canvas


def run_for_img(img, img_location, headers):
    for y_index, row in enumerate(img):
        print('Getting current canvas status')
        canvas = get_pixels(headers)
        print('Got current canvas status')

        for x_index, colour_code in enumerate(row):
            pix_y = img_location['y'] + y_index
            pix_x = img_location['x'] + x_index

            if canvas[pix_y][pix_x] == colours[colour_code]:
                print(f'Pixel at ({pix_x}, {pix_y}) is {colours[colour_code]} as intended')
                continue
            else:
                print(f'Pixel at ({pix_x}, {pix_y}) will be made {colours[colour_code]}')
                set_pixel(x=pix_x, y=pix_y, rgb=colours[colour_code], headers=headers)


def main():
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    print('Loaded config')

    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }

    print(f'sleeping for {STARTUP_DELAY} seconds')
    time.sleep(STARTUP_DELAY)
    while True:
        for zone in zones_to_do:
            img = zone['img']
            img_location = zone['img_location']

            print(f"img name: {zone['name']}")
            print(f'img dimension x: {len(img[0])}')
            print(f'img dimension y: {len(img)}')
            print(f'img pixels: {len(img[0]) * len(img)}')
            run_for_img(img, img_location, headers)


if __name__ == '__main__':
    main()
