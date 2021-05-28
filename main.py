#!/usr/bin/env python

import json
import sys
import typing
import re
import time
import tkinter
import threading
import logging
import argparse
from pathlib import Path

import requests
from requests.structures import CaseInsensitiveDict
import PIL.Image


__version__ = '3.0.0'


# modify this to change the order of priority or add/remove images
imgs = [
    "cmpc",
    "httpscmpclivetwitchtvcontrolmypc-utf-8",
    "wbub",
    "jmcb",
    "voxelfox",
    "httpsvflgg-utf-8",
    "JMcB-utf-8",
    "sqlitecult",
    "pydispix",
]


CONFIG_FILE_PATH = Path('config.json')
IMGS_FOLDER = Path('imgs')
CANVAS_LOG_PATH = Path('canvas.log')
DEBUG_LOG_PATH = Path('debug.log')
CANVAS_IMAGE_PATH = Path('imgs') / 'upscale' / 'canvas.png'
WORM_COLOUR = 'ff8983'
BASE_URL = 'https://pixels.pythondiscord.com'
SET_URL = f'{BASE_URL}/set_pixel'
GET_SIZE_URL = f'{BASE_URL}/get_size'
GET_PIXELS_URL = f'{BASE_URL}/get_pixels'
GET_PIXEL_URL = f'{BASE_URL}/get_pixel'
GUI_SCALE = 5
STARTUP_DELAY = 120


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
for logger_name in ['urllib3', 'PIL']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)


class GUIThread(threading.Thread):
    def __init__(self, canvas_size: dict, activate: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.startup_barrier = threading.Barrier(2)

        self.canvas_size = canvas_size
        self.activate = activate

        self.tk = None
        self.tk_canvas = None
        self.tk_img = None

    def run(self) -> None:
        w = self.canvas_size['width'] * GUI_SCALE
        h = self.canvas_size['height'] * GUI_SCALE

        self.tk = tkinter.Tk()
        self.tk.title('pydis-pixels')
        self.tk.resizable(width=False, height=False)
        self.tk.geometry(f'{w}x{h}')
        self.tk_canvas = tkinter.Canvas(self.tk, bg='#ffffff', width=w, height=h)
        self.tk_canvas.pack()
        self.tk_img = tkinter.PhotoImage(
            name='Pixels', width=w, height=h
        )
        self.tk_canvas.create_image(
            (w/2, h/2), image=self.tk_img, state='normal'
        )

        self.startup_barrier.wait()
        if self.activate:
            logging.info('Starting GUI canvas display with dimensions %sx%s', w, h)
            self.tk.mainloop()


def get_parser() -> argparse.ArgumentParser:
    """Get this script's parser."""
    parser = argparse.ArgumentParser(
        description=f'load images and their coords from {IMGS_FOLDER} and try to create/protect them'
    )

    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('-g', '--gui', action='store_true', help='run a live tkinter display of the canvas')

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


def print_sleep_time(duration):
    logging.info(f'sleeping for {duration} seconds')
    sleep_finish_time = time.asctime(time.localtime(time.time() + duration))
    logging.info(f'finish sleeping at {sleep_finish_time}')


def ratelimit(headers: CaseInsensitiveDict):
    """Given headers from a response, print info and sleep if needed."""
    if 'requests-remaining' in headers:
        requests_remaining = int(headers['requests-remaining'])
        logging.info(f'{requests_remaining} requests remaining')
        if not requests_remaining:
            requests_reset = int(headers['requests-reset'])
            print_sleep_time(requests_reset)
            time.sleep(requests_reset)
    else:
        cooldown_reset = int(headers['cooldown-reset'])
        logging.info('on cooldown')
        print_sleep_time(cooldown_reset)
        time.sleep(cooldown_reset)


def set_pixel(x: int, y: int, rgb: str, headers: dict):
    """set_pixel endpoint wrapper."""
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
    logging.info(r.json()['message'])

    ratelimit(r.headers)


def get_pixels(canvas_size: dict, headers: dict, as_bytes: bool = False) -> typing.Union[img_type, bytes]:
    """get_pixels endpoint wrapper.

    Returns as a 2d list of hex colour strings, like an img.
    """
    r = requests.get(
        GET_PIXELS_URL,
        headers=headers
    )
    ratelimit(r.headers)

    pixels_bytes = r.content
    with open(CANVAS_LOG_PATH, 'a', encoding='utf-8') as canvas_log_file:
        canvas_log_file.write(f'{time.asctime()}\n{pixels_bytes}\n')
    if as_bytes:
        return pixels_bytes

    canvas = []
    for y in range(canvas_size['height']):
        row = []
        for x in range(canvas_size['width']):
            index = (y * canvas_size['width'] * 3) + (x * 3)
            pixel = pixels_bytes[index:index+3]
            row.append(three_bytes_to_rgb_hex_string(pixel))
        canvas.append(row)

    return canvas


def get_pixel(x: int, y: int, headers: dict) -> str:
    """get_pixel endpoint wrapper."""
    params = {
        'x': x,
        'y': y
    }
    r = requests.get(
        GET_PIXEL_URL,
        params=params,
        headers=headers
    )
    ratelimit(r.headers)
    return r.json()['rgb']


def get_size(headers: dict) -> typing.Dict[str, int]:
    """get_size endpoint wrapper."""
    r = requests.get(
        GET_SIZE_URL,
        headers=headers
    )

    return r.json()


def save_canvas_as_png(canvas_size, headers, path: typing.Union[str, Path] = None):
    if path is None:
        path = CANVAS_IMAGE_PATH

    canvas_bytes = get_pixels(canvas_size, headers, as_bytes=True)
    canvas_pil_img = PIL.Image.frombytes(
        mode='RGB',
        size=(canvas_size['width'], canvas_size['height']),
        data=canvas_bytes
    )
    canvas_pil_img.save(path)


def put_scaled_pixel(tk_img: tkinter.PhotoImage, colour: str, location: typing.Tuple[int, int], scale: int = GUI_SCALE):
    fcolour = f'#{colour}'
    slocation = [c * scale for c in location]
    for y in range(scale):
        for x in range(scale):
            tk_img.put(fcolour, (slocation[0] + x, slocation[1] + y))


def render_img_tk(gui_thread: GUIThread, img: img_type, scale: int = GUI_SCALE):
    for y_index, row in enumerate(img):
        for x_index, pixel in enumerate(row):
            if pixel:
                gui_thread.tk_img.put(f'#{pixel}', (x_index, y_index))

    w = gui_thread.tk_img.width()
    h = gui_thread.tk_img.height()
    tk_img = gui_thread.tk_img.zoom(scale)
    gui_thread.tk_canvas.delete('Pixels')
    gui_thread.tk_canvas.create_image(
        (w / 2, h / 2), image=tk_img, state='normal'
    )
    tkinter.Label(gui_thread.tk, image=tk_img)


def run_for_img(zone: Zone, canvas_size: dict, gui_thread: GUIThread, headers: dict):
    """Given an img and the location of its top-left corner on the canvas, draw/repair that image."""
    img = zone.img
    img_location = zone.location

    logging.info('Getting current canvas status')
    canvas = get_pixels(canvas_size, headers)
    render_img_tk(gui_thread, canvas)
    logging.info('Got current canvas status')

    for y_index, row in enumerate(img):
        hit_incorrect_pixel = False

        for x_index, colour in enumerate(row):
            pix_y = img_location['y'] + y_index
            pix_x = img_location['x'] + x_index

            # get canvas every other time
            # getting it more often means better collaboration
            # but too often is too often
            # also only do it if we've hit a zone that needs changing, to further prevent get_pixel rate limiting
            if hit_incorrect_pixel and x_index % 2 == 0:
                logging.info(f'Getting status of pixel at ({pix_x}, {pix_y})')
                new_pixel = get_pixel(pix_x, pix_y, headers)
                canvas[pix_y][pix_x] = new_pixel
                put_scaled_pixel(gui_thread.tk_img, new_pixel, (pix_x, pix_y))
                logging.info(f'Got status of pixel at ({pix_x}, {pix_y}), {canvas[pix_y][pix_x]}')

            if colour is None:
                logging.info(f'Pixel at ({pix_x}, {pix_y}) is intended to be transparent, skipping')
            elif canvas[pix_y][pix_x] == colour:
                logging.info(f'Pixel at ({pix_x}, {pix_y}) is {colour} as intended')
            elif colour == WORM_COLOUR:
                logging.info('Oh, worm')
            else:
                hit_incorrect_pixel = True
                logging.info(f'Pixel at ({pix_x}, {pix_y}) will be made {colour}')
                set_pixel(x=pix_x, y=pix_y, rgb=colour, headers=headers)
                put_scaled_pixel(gui_thread.tk_img, colour, (pix_x, pix_y))


def main():
    """Run the program for all imgs."""
    parser = get_parser()
    args = parser.parse_args()

    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)
    logging.info('Loaded config')
    bearer_token = f"Bearer {config['token']}"
    headers = {
        "Authorization": bearer_token
    }

    print_sleep_time(STARTUP_DELAY)
    time.sleep(STARTUP_DELAY)

    logging.info('Getting canvas size')
    canvas_size = get_size(headers)
    logging.info(f'Canvas size: {canvas_size}')

    logging.info(f'Saving current canvas as png to {CANVAS_IMAGE_PATH}')
    save_canvas_as_png(canvas_size, headers)

    logging.info(f'Loading zones to do from {IMGS_FOLDER}')
    zones_to_do = load_zones(IMGS_FOLDER, imgs)
    total_area = sum(z.area_not_transparent for z in zones_to_do)
    logging.info(f'Total area: {total_area}')
    canvas_area = canvas_size['width'] * canvas_size['height']
    total_area_percent = round(((total_area / canvas_area) * 100), 2)
    logging.info(f'Total area: {total_area_percent}% of canvas')

    gui_thread = GUIThread(canvas_size=canvas_size, activate=args.gui)
    gui_thread.start()
    gui_thread.startup_barrier.wait()

    while True:
        try:
            for zone in zones_to_do:
                logging.info(f"img name: {zone.name}")
                logging.info(f'img dimension x: {zone.width}')
                logging.info(f'img dimension y: {zone.height}')
                logging.info(f'img pixels: {zone.area_not_transparent}')
                run_for_img(zone, canvas_size, gui_thread, headers)
        except Exception as error:
            logging.error(error)


if __name__ == '__main__':
    main()
