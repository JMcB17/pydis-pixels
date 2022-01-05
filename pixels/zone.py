import logging
import re
from pathlib import Path
from typing import Union


from PIL import Image


log = logging.getLogger(__name__)


def scale_image(image: Image.Image, scale: int) -> Image.Image:
    """Calculate the new size of a PIL image, resize and return it."""
    new_size = (
        image.width // scale,
        image.height // scale
    )
    return image.resize(size=new_size, resample=Image.NEAREST)


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

    def __init__(self, image_path: Union[str, Path]):
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
        image_path = Path(image_path)
        self.image_path = image_path

        filename = self.image_path.stem
        properties = re.match(self.img_name_regexp, filename)
        self.name = properties[1]
        self.scale = int(properties[2])
        self.location = {
            'x': int(properties[3]),
            'y': int(properties[4])
        }

        image = Image.open(self.image_path)
        image = image.convert('RGBA')
        self.image_unscaled = image
        if self.scale != 1:
            self.image = scale_image(self.image_unscaled, self.scale)
        else:
            self.image = self.image_unscaled
        self.width, self.height = self.image.size
        self.area = self.width * self.height

        self.area_not_transparent = self.area
        for row in self.image:
            for pixel in row:
                if pixel is None:
                    self.area_not_transparent -= 1

        log.info(
            f'Loaded zone {self.name}\n'
            f'    width:  {self.width}\n'
            f'    height: {self.height}\n'
            f'    area:   {self.area}'
        )


def load_zones(directory: Path, img_names: list[str]) -> list[Zone]:
    """Load zones that match img_names from directory and return them."""
    zones = []

    for img in img_names:
        for file in directory.iterdir():
            if file.name.startswith(img) and file.is_file():
                zones.append(Zone(file))
                break
        else:
            log.error('Unable to find file for zone with name %s', img)

    return zones
