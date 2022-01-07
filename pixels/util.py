from typing import Union
from PIL import Image


def rgb_to_hex(rgb_ints: Union[list[int], bytes], prefix: str = '#') -> str:
    """Take a list of ints and convert it to a colour e.g. [255, 255, 255] -> ffffff."""
    return '{prefix}{:02x}{:02x}{:02x}'.format(*rgb_ints, prefix=prefix)


def bytes_to_image(image_bytes: bytes, width: int, height: int) -> Image.Image:
    return Image.frombytes(
        mode='RGB',
        size=(width, height),
        data=image_bytes
    )


def scale_image(image: Image.Image, scale: int, down: bool = True) -> Image.Image:
    """Calculate the new size of a PIL image, resize and return it."""
    if down:
        new_size = (
            image.width // scale,
            image.height // scale
        )
    else:
        new_size = (
            image.width * scale,
            image.height * scale
        )
    return image.resize(size=new_size, resample=Image.NEAREST)
