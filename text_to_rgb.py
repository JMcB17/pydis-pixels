#!/usr/bin/env python

from pathlib import Path
import PIL.Image
from main import three_bytes_to_rgb_hex_string


IGNORED_FOLDER = Path('imgs') / 'upscale'


def main():
    text = input('Text: ')
    scale = int(input('Scale: '))
    if not scale:
        scale = 1

    text_encoded = text.encode('utf-8')

    padded_length = len(text_encoded) + (3 - len(text_encoded) % 3)
    text_encoded_padded = text_encoded.ljust(padded_length, b' ')

    for i in range(len(text_encoded_padded) // 3):
        colour = three_bytes_to_rgb_hex_string(text_encoded_padded[i*3:i*3 + 3])
        print(colour)

    img_size = (len(text_encoded_padded) // 3, 1)
    img = PIL.Image.frombytes(mode='RGB', size=img_size, data=text_encoded_padded)
    if scale != 1:
        new_size = (img.width*scale, img.height*scale)
        img_scaled = img.resize(new_size, resample=PIL.Image.NEAREST)
    else:
        img_scaled = img
    img_name = f'{text},{scale}x,(,).png'
    img_scaled.save(IGNORED_FOLDER / img_name)


if __name__ == '__main__':
    main()
