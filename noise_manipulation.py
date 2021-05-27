import random
import typing

import main


HEX_CHARS = '0123456789abcdef'


def add_noise(canvas_size: dict, headers: dict):
    """Do not use."""
    x_coord = random.randint(0, canvas_size['width'])
    y_coord = random.randint(0, canvas_size['height'])
    colour = ''.join(random.choices(HEX_CHARS, k=6))
    main.set_pixel(x_coord, y_coord, colour, headers)


def get_neighbour_pixels(x: int, y: int, img: main.img_type) -> typing.List[str]:
    """Return the eight pixels that neighbour the given co-ordinates.

    Raises IndexError if the pixel is a corner pixel and thus has less than eight neighbours.
    """
    neighbours = []
    for y_neighbour_coord in [y-1, y, y+1]:
        x_neighbour_range = [x-1, x, x+1]
        if y_neighbour_coord == y:
            x_neighbour_range.remove(x)

        for x_neighbour_coord in x_neighbour_range:
            neighbours.append(img[y_neighbour_coord][x_neighbour_coord])

    return neighbours


def remove_noise(img: main.img_type, headers: dict, same_neighbour_threshold: int = 7):
    """Try to remove some noise.

    If any pixel in img is surrounded by at least same_neighbour_threshold (default 7) of the same colour,
    and pixel is not that colour, set pixel to that colour.
    """
    for y_coord, row in enumerate(img):
        for x_coord, pixel in enumerate(row):
            try:
                pixel_neighbours = get_neighbour_pixels(x_coord, y_coord, img)
            except IndexError:
                continue

            unique_pixel_neighbours = list(set(pixel_neighbours))
            unique_pixel_neighbours.sort(key=lambda p: pixel_neighbours.count(p), reverse=True)
            highest_incidence_neighbour = unique_pixel_neighbours[0]
            if pixel_neighbours.count(highest_incidence_neighbour) >= same_neighbour_threshold:
                img[y_coord][x_coord] = highest_incidence_neighbour
                main.set_pixel(x_coord, y_coord, highest_incidence_neighbour, headers)
