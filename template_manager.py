"""https://gist.github.com/LittleEndu/b899077a03b60080f1a1f719c3e12de7"""

import datetime
import json
import typing
from pathlib import Path

from PIL import Image

CANVAS_START = datetime.datetime(2021, 5, 24)

templates = {}


class Template:
    def __init__(self, directory: typing.Union[str, Path]):
        if not isinstance(directory, Path):
            directory = Path(directory)

        self.directory = directory
        json_path = self.directory / 'canvas.json'
        if not json_path.is_file():
            raise ValueError("directory must contain canvas.json")
        with open(json_path) as json_in:
            json_data = json.load(json_in)
        self.single_duration = json_data['minutesPerFrame'] * 60
        self.left = json_data['left']
        self.top = json_data['top']
        self.current_frame = None
        self.length = len(list(self.directory.iterdir())) - 1

    def get_current_frame_index(self):
        if self.single_duration <= 0:
            changed = self.current_frame != 0
            self.current_frame = 0
            return 0, changed
        elapsed = (datetime.datetime.utcnow() - CANVAS_START).total_seconds()
        index = int((elapsed / self.single_duration) % self.length)
        changed = self.current_frame != index
        self.current_frame = index
        return index, changed

    def get_current_frame_path(self):
        index, changed = self.get_current_frame_index()
        return self.directory / sorted([i for i in self.directory.iterdir() if i != 'canvas.json'])[index], changed


def get_template_for(directory: Path):
    abs_path = directory.resolve()
    return templates.setdefault(abs_path, Template(abs_path))


def reset_templates_cache():
    global templates
    templates = {}


def convert_frames_to_absolute(directory: Path):
    abs_path = directory.resolve()
    template = templates.setdefault(abs_path, Template(abs_path))
    ww = None
    hh = None

    for i in abs_path.iterdir():
        img_path = abs_path / i
        if i == "canvas.json":
            continue
        img = Image.open(img_path)
        if ww is None:
            ww = img.size[0] + template.left
            hh = img.size[1] + template.top
        converter = Image.new('RGBA', (ww, hh))
        converter.paste(img, (template.left, template.top))
        img.close()
        converter.save(img_path)

    template.left = 0
    template.top = 0
    with open(abs_path / 'canvas.json', 'w') as json_out:
        json.dump({
            "minutesPerFrame": template.single_duration / 60,
            "left": 0,
            "top": 0
        }, json_out)


def convert_frames_to_relative(directory: Path):
    raise NotImplemented('Join (0, 0) master race now')


def main():
    abs_conversion_path = Path('convert_to_absolute')
    if abs_conversion_path.is_dir():
        for i in abs_conversion_path.iterdir():
            convert_frames_to_absolute(abs_conversion_path / i)

    rel_conversion_path = Path('convert_to_relative')
    if rel_conversion_path.is_dir():
        for i in rel_conversion_path.iterdir():
            convert_frames_to_relative(rel_conversion_path / i)


if __name__ == '__main__':
    main()
