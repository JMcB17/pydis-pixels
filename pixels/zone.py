import json
import logging
from pathlib import Path
from typing import Union

from PIL import Image
from . import util


IMAGES_FOLDER = Path('images')
Image2D = list[list[str]]

log = logging.getLogger(__name__)


class Zone:
    """An area of pixels on the canvas, to be maintained."""

    def __init__(self, json_path: Union[str, Path]):
        """Load a zone from its json definition file."""
        json_path = Path(json_path)
        self.json_path = json_path

        with open(json_path) as json_file:
            zone_definition = json.load(json_file)
        try:
            self.name = zone_definition['name']
            self.image_path = IMAGES_FOLDER / zone_definition['image']
            self.coords = tuple(zone_definition['coords'])
            self.scale = zone_definition['scale']
        except KeyError as error:
            raise ValueError(
                f'The metadata "{error.args[0]}" is missing from the zone "{json_path.name}".'
            ) from error

        image = Image.open(self.image_path)
        image = image.convert('RGBA')
        self.image_unscaled = image
        if self.scale != 1:
            self.image = util.scale_image(self.image_unscaled, self.scale)
        else:
            self.image = self.image_unscaled
        self.width, self.height = self.image.size
        self.area = self.width * self.height

        area_opaque = self.area
        for y in range(self.image.height):
            for x in range(self.image.width):
                pixel = self.image.getpixel((x, y))
                if pixel[3]:
                    area_opaque -= 1
        self.area_opaque = area_opaque

        log.info(
            f'Loaded zone {self.name}\n'
            f'    width:  {self.width}\n'
            f'    height: {self.height}\n'
            f'    area:   {self.area}'
        )


def load_zones(directory: Union[str, Path]) -> list[Zone]:
    """Load zones that match img_names from directory and return them."""
    directory = Path(directory)
    zones = []

    for path in directory.iterdir():
        if path.is_file() and path.suffix == '.json':
            zones.append(Zone(path))

    return zones
