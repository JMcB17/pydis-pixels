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


def ratelimit(headers):
    requests_remaining = int(headers['requests-remaining'])
    print(f'{requests_remaining} requests remaining')
    if not requests_remaining:
        requests_reset = int(headers['requests-reset'])
        print(f'sleeping for {requests_reset} seconds')
        time.sleep(requests_reset)


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

    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }


if __name__ == '__main__':
    main()
