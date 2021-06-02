"""https://gist.github.com/LittleEndu/b899077a03b60080f1a1f719c3e12de7"""

import datetime
import json
import os.path

from PIL import Image

CANVAS_START = datetime.datetime(2021, 5, 24)

templates = {}


class Template:
    def __init__(self, directory):
        self.directory = directory
        json_path = os.path.join(directory, 'canvas.json')
        if not os.path.isfile(json_path):
            raise ValueError("directory must contain canvas.json")
        with open(json_path) as json_in:
            json_data = json.load(json_in)
        self.single_duration = json_data['minutesPerFrame'] * 60
        self.left = json_data['left']
        self.top = json_data['top']
        self.current_frame = None
        self.length = len(os.listdir(self.directory)) - 1

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
        return os.path.join(
            self.directory,
            sorted([i for i in os.listdir(self.directory) if i != 'canvas.json'])[index]
        ), changed


def get_template_for(directory):
    abs_path = os.path.abspath(directory)
    return templates.setdefault(abs_path, Template(abs_path))


def reset_templates_cache():
    global templates
    templates = {}


def convert_frames_to_absolute(directory):
    abs_path = os.path.abspath(directory)
    template = templates.setdefault(abs_path, Template(abs_path))
    ww = None
    hh = None

    for i in os.listdir(abs_path):
        img_path = os.path.join(abs_path, i)
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
    with open(os.path.join(abs_path, 'canvas.json'), 'w') as json_out:
        json.dump({
            "minutesPerFrame": template.single_duration / 60,
            "left": 0,
            "top": 0
        }, json_out)


def convert_frames_to_relative(directory):
    raise NotImplemented('Join (0, 0) master race now')


if __name__ == '__main__':
    if os.path.isdir('convert_to_absolute'):
        for i in os.listdir('convert_to_absolute'):
            convert_frames_to_absolute(os.path.join('convert_to_absolute', i))
    if os.path.isdir('convert_to_relative'):
        for i in os.listdir('convert_to_relative'):
            convert_frames_to_relative(os.path.join('convert_to_relative', i))
