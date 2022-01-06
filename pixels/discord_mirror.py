import json
import io
from datetime import datetime, timezone

import aiohttp
from PIL import Image

from . import scale_image


__version__ = '3.0.0'


EMBED_TITLE = 'Pixels State'
EMBED_FOOTER = 'Last updated'
WEBHOOK_USERNAME = 'Pixels-mirror'
WEBHOOK_AVATAR_URL = 'https://cdn.discordapp.com/app-icons/848597264192110622/7cbfb4c8580b767fb167a209aa1e2587.png'
FILE_NAME_FORMAT = 'pixels_mirror_{timestamp}.png'
IMAGE_SCALE = 5


# https://discord.com/developers/docs/resources/webhook
# https://github.com/python-discord/pixels/blob/main/pixels/endpoints/moderation.py


def get_embed(now: datetime) -> dict:
    embed = {
        'title': EMBED_TITLE,
        'footer': {'text': EMBED_FOOTER},
        'timestamp': now.isoformat()
    }
    return embed


async def create_mirror(webhook_url: str) -> int:
    now = datetime.now(timezone.utc)
    embed = get_embed(now)

    payload_json = {
        'content': '',
        'embeds': [embed],
        'username': WEBHOOK_USERNAME,
        'avatar_url': WEBHOOK_AVATAR_URL,
    }
    data = {'payload_json': json.dumps(payload_json)}

    async with aiohttp.ClientSession() as session:
        r = await session.post(url=webhook_url, data=data)
        r_json = await r.json()

    return r_json['id']


async def edit_embed_file(webhook_url: str, embed: dict, stream: io.BytesIO, now: datetime):
    file_name = FILE_NAME_FORMAT.format(timestamp=now.timestamp())
    embed['image'] = {'url': f'attachment://{file_name}'}
    discord_file = {
        'name': 'file',
        'value': stream.getvalue(),
        'filename': file_name,
        'content_type': 'application/octet-stream'
    }

    payload_json = {
        'content': '',
        'embeds': [embed],
        # get rid of the previous attachments
        'attachments': []
    }

    async with aiohttp.ClientSession() as session:
        await session.patch(url=webhook_url, data=data)


async def update_mirror(canvas: Image.Image, message_id: int, webhook_url: str):
    canvas_scaled = scale_image(canvas, IMAGE_SCALE)
    with io.BytesIO() as byte_stream:
        canvas_scaled.save(byte_stream, format='PNG')
        byte_stream.seek(0)

    now = datetime.now(timezone.utc)
    embed = get_embed(now)
