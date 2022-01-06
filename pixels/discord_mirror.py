import io
import json
from datetime import datetime, timezone

import aiohttp
from PIL import Image

from . import util


__version__ = '3.0.0'


EMBED_TITLE = 'Pixels State'
EMBED_FOOTER = 'Last updated'
WEBHOOK_USERNAME = 'Pixels-mirror'
WEBHOOK_AVATAR_URL = 'https://cdn.discordapp.com/app-icons/848597264192110622/7cbfb4c8580b767fb167a209aa1e2587.png'
FILE_NAME_FORMAT = 'pixels_mirror_{timestamp}.png'
IMAGE_SCALE = 5


# https://discord.com/developers/docs/resources/webhook
# https://discord.com/developers/docs/reference#uploading-files
# https://github.com/python-discord/pixels/blob/main/pixels/endpoints/moderation.py


def get_embed(now: datetime) -> dict:
    embed = {
        'title': EMBED_TITLE,
        'footer': {'text': EMBED_FOOTER},
        'timestamp': now.isoformat()
    }
    return embed


async def create_mirror(webhook_url: str) -> aiohttp.ClientResponse:
    now = datetime.now(timezone.utc)
    embed = get_embed(now)
    payload_json = {
        'embeds': [embed],
        'username': WEBHOOK_USERNAME,
        'avatar_url': WEBHOOK_AVATAR_URL,
    }
    async with aiohttp.ClientSession() as session:
        return await session.post(url=webhook_url, json=payload_json)


async def edit_webhook(stream: io.BytesIO, message_id: int, webhook_url: str) -> aiohttp.ClientResponse:
    now = datetime.now(timezone.utc)
    embed = get_embed(now)
    file_name = FILE_NAME_FORMAT.format(timestamp=now.timestamp())
    embed['image'] = {'url': f'attachment://{file_name}'}

    attachment = {
        'id': 0,
        'description': EMBED_TITLE,
        'filename': file_name,
    }
    payload_json = {
        'embeds': [embed],
        'attachments': [attachment],
        'message_reference': {'message_id': message_id},
    }

    form_data = aiohttp.FormData()
    form_data.add_field(
        name='payload_json',
        value=json.dumps(payload_json),
        content_type='application/json'
    )
    form_data.add_field(
        name='file[0]',
        value=stream.getvalue(),
        content_type='image/png',
        filename=file_name
    )

    async with aiohttp.ClientSession() as session:
        return await session.patch(url=webhook_url, data=form_data)


async def update_mirror(canvas: Image.Image, message_id: int, webhook_url: str):
    canvas_scaled = util.scale_image(canvas, IMAGE_SCALE)
    with io.BytesIO() as stream:
        canvas_scaled.save(stream, format='PNG')
        stream.seek(0)

        return await edit_webhook(stream, message_id, webhook_url)
