#!/usr/bin/env python

import json
import time
from pathlib import Path

import requests


CONFIG_FILE_PATH = Path('config.json')
BASE_URL = 'https://pixels.pythondiscord.com'
SET_URL = f'{BASE_URL}/set_pixel'
GET_SIZE_URL = f'{BASE_URL}/get_size'
GET_PIXELS_URL = f'{BASE_URL}/get_pixels'
CANVAS_SIZE = {
    'width': 160,
    'height': 90,
}

# JMCB
img = [
    [1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1],
    [1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0],
]
# CMPC
img2 = [
    [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1],
    [1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0],
    [1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1],
]
print(f'img dimension x: {len(img[0])}')
print(f'img dimension y: {len(img)}')
print(f'img pixels: {len(img[0]) * len(img)}')
# noinspection SpellCheckingInspection
target_colour = '1dbfff'
blank_colour = 'ffffff'
img_location = {
    'x': 75,
    'y': 2
}


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


def three_bytes_to_rgb_hex_string(pixel: bytes) -> str:
    rgb_ints = [b for b in pixel]
    rgb_hex = [hex(i) for i in rgb_ints]
    rgb_hex_strings = [str(h).removeprefix('0x') for h in rgb_hex]
    rgb_hex_string = ''.join(rgb_hex_strings)

    return rgb_hex_string


def get_pixels(headers: dict):
    r = requests.get(
        GET_PIXELS_URL,
        headers=headers
    )
    pixels_bytes = r.content
    canvas = []
    for y in range(CANVAS_SIZE['height']+1):
        row = []
        for x in range(CANVAS_SIZE['width']+1):
            index = (y * CANVAS_SIZE['width'] * 3) + (x * 3)
            pixel = pixels_bytes[index:index+3]
            row.append(three_bytes_to_rgb_hex_string(pixel))
        canvas.append(row)

    return canvas


def main():
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    print('Loaded config')

    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }

    while True:
        print('Getting current canvas status')
        canvas = get_pixels(headers)
        print('Got current canvas status')

        for y_index, row in enumerate(img):
            for x_index, pix_active in enumerate(row):
                pix_y = img_location['y'] + y_index
                pix_x = img_location['x'] + x_index

                if pix_active and canvas[pix_y][pix_x] == target_colour:
                    print(f'Pixel at ({pix_x}, {pix_y}) is target colour as intended')
                    continue
                elif not pix_active and canvas[pix_y][pix_x] == blank_colour:
                    print(f'Pixel at ({pix_x}, {pix_y}) is blank as intended')
                    continue
                elif pix_active:
                    print(f'Pixel at ({pix_x}, {pix_y}) will be made target colour')
                    set_pixel(x=pix_x, y=pix_y, rgb=target_colour, headers=headers)
                else:
                    print(f'Pixel at ({pix_x}, {pix_y}) will be made blank')
                    set_pixel(x=pix_x, y=pix_y, rgb=blank_colour, headers=headers)


if __name__ == '__main__':
    main()
