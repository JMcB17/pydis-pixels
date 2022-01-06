from random import choices, randint

from PIL import Image
import api


__version__ = '0.1.0'

HEX_CHARS = '0123456789abcdef'


def add_noise(canvas_size: dict, headers: dict):
    """Do not use."""
    x_coord = randint(0, canvas_size['width'])
    y_coord = randint(0, canvas_size['height'])
    colour = ''.join(choices(HEX_CHARS, k=6))
    api.set_pixel(x_coord, y_coord, colour, headers)


def get_neighbour_pixels(x: int, y: int, image: Image.Image) -> list[str]:
    """Return the eight pixels that neighbour the given co-ordinates.

    Raises IndexError if the pixel is a corner pixel and thus has less than eight neighbours.
    """
    neighbours = []
    for y_neighbour_coord in [y-1, y, y+1]:
        x_neighbour_range = [x-1, x, x+1]
        if y_neighbour_coord == y:
            x_neighbour_range.remove(x)

        for x_neighbour_coord in x_neighbour_range:
            if x_neighbour_coord < 0 or y_neighbour_coord < 0:
                raise IndexError('pixel is edge pixel')

            try:
                neighbours.append(image.getpixel((x_neighbour_coord, y_neighbour_coord)))
            except IndexError as error:
                raise IndexError('pixel is edge pixel') from error

    return neighbours


def remove_noise(image: Image.Image, headers: dict, same_neighbour_threshold: int = 7):
    """Try to remove some noise.

    If any pixel in img is surrounded by at least same_neighbour_threshold (default 7) of the same colour,
    and pixel is not that colour, set pixel to that colour.
    """
    for y in range(image.height):
        for x in range(image.width):
            try:
                pixel_neighbours = get_neighbour_pixels(x, y, image)
            except IndexError:
                continue

            unique_pixel_neighbours = list(set(pixel_neighbours))
            unique_pixel_neighbours.sort(key=lambda p: pixel_neighbours.count(p), reverse=True)
            highest_incidence_neighbour = unique_pixel_neighbours[0]
            if pixel_neighbours.count(highest_incidence_neighbour) >= same_neighbour_threshold:
                image.putpixel((x, y), highest_incidence_neighbour)
                api.set_pixel(x, y, highest_incidence_neighbour, headers)
