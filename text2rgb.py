import argparse
from pathlib import Path

from PIL import Image
from pixels import rgb_to_hex


__version__ = '1.2.0'


IGNORED_FOLDER = Path('images/ignore')
ENCODING = 'utf-8'


def get_parser() -> argparse.ArgumentParser:
    """Get this script's parser."""
    parser = argparse.ArgumentParser(description='convert text to colours codes and an image')

    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('text', nargs='?', help='the text to convert')
    parser.add_argument('-s', '--scale', type=int, default=1, help='scale up the image this much before saving it')
    parser.add_argument('-e', '--encoding', default=ENCODING, help='encoding for text, default %(default)s')

    return parser


def sanitise_filename(string: str) -> str:
    """Remove non-alphanumeric characters."""
    sanitised_list = []
    for char in string:
        if char.isalnum():
            sanitised_list.append(char)

    return ''.join(sanitised_list)


def main():
    """Take input and print the colours then save an image."""
    parser = get_parser()
    args = parser.parse_args()

    if not args.text:
        args.text = input('Text: ')

    text_encoded = args.text.encode(args.encoding)

    padded_length = len(text_encoded) + (3 - len(text_encoded) % 3)
    text_encoded_padded = text_encoded.ljust(padded_length, bytes([0]))

    for i in range(len(text_encoded_padded) // 3):
        colour = rgb_to_hex(text_encoded_padded[(i*3):(i*3 + 3)])
        print(colour)

    image_size = (len(text_encoded_padded) // 3, 1)
    image = Image.frombytes(mode='RGB', size=image_size, data=text_encoded_padded)
    if args.scale != 1:
        new_size = (image.width*args.scale, image.height*args.scale)
        image_scaled = image.resize(new_size, resample=Image.NEAREST)
    else:
        image_scaled = image
    image_name = f'{sanitise_filename(args.text)}-{args.encoding}-{args.scale}x.png'
    image_path = IGNORED_FOLDER / image_name
    print(f'Writing image to "{image_path}".')
    image_scaled.save(image_path)
    print('Done!')


if __name__ == '__main__':
    main()
