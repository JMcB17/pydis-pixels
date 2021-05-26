#!/usr/bin/env python


from main import three_bytes_to_rgb_hex_string


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


if __name__ == '__main__':
    main()