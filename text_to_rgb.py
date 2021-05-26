#!/usr/bin/env python

import typing
import PIL.Image
from main import three_bytes_to_rgb_hex_string


def hex_string_to_tuple(hex_string: str) -> typing.Tuple[int]:
    converted = []
    for num in [hex_string[0:2], hex_string[2:4], hex_string[4:6]]:
        converted.append(int(f'0x{num}', 16))
    return tuple(converted)


def main():
    text = input('Text: ')
    text_encoded = text.encode('utf-8')

    padded_length = len(text_encoded) + (3 - len(text_encoded) % 3)
    text_encoded_padded = text_encoded.ljust(padded_length, b' ')

    colours = []
    for i in range(len(text_encoded_padded) // 3):
        colour = three_bytes_to_rgb_hex_string(text_encoded_padded[i*3:i*3 + 3])
        print(colour)
        colours.append(colour)

    colours_tuples = [hex_string_to_tuple(h) for h in colours]
    img_bytes = b''
    for colour_tuple in colours_tuples:
        img_bytes += bytes(colour_tuple)

    img_size = (len(colours_tuples), 1)
    img = PIL.Image.frombytes(mode='RGB', size=img_size, data=img_bytes)
    img.save('test.png')


if __name__ == '__main__':
    main()
