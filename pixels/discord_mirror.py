import io
from datetime import datetime, timezone

import aiohttp
import discord

from . import bytes_to_image, scale_image


__version__ = '3.0.0'


EMBED_TITLE = 'Pixels State'
EMBED_FOOTER = 'Last updated'
FILE_NAME_FORMAT = 'pixels_mirror_{timestamp}.png'
IMAGE_SCALE = 5


def get_embed() -> discord.Embed:
    embed = discord.Embed(title=EMBED_TITLE)
    embed.set_footer(text=EMBED_FOOTER)
    embed.timestamp = datetime.now(timezone.utc)
    return embed


async def create_mirror(webhook_url: str) -> int:
    embed = get_embed()
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            webhook_url, adapter=discord.AsyncWebhookAdapter(session)
        )
        webhook_message = await webhook.send(embed=embed)

    return webhook_message.id


# todo: avatar url
async def edit_embed_file(embed: discord.Embed):
    # todo: redo this with official methods when new discord.py version releases
    embed_dict = embed.to_dict()
    payload_dict = {
        'embed': embed_dict,
        # get rid of the previous attachments
        'attachments': []
    }

    discord_file_json = {
        'name': 'file',
        'value': canvas_discord_file.fp,
        'filename': canvas_discord_file.filename,
        'content_type': 'application/octet-stream'
    }

    form = [
        {
            'name': 'payload_json',
            'value': discord.utils.to_json(payload_dict),
        },
        discord_file_json
    ]

    route = discord.http.Route(
        'PATCH', '/channels/{channel_id}/messages/{message_id}',
        channel_id=discord_message.channel.id, message_id=discord_message.id
    )
    data = await discord_message._state.http.request(
        route, files=[canvas_discord_file], form=form,
    )
    discord_message._update(data)
    canvas_discord_file.close()


async def update_mirror(canvas_bytes: bytes, message_id: int, webhook_url: str, width: int, height: int):
    canvas = bytes_to_image(canvas_bytes, width, height)
    canvas_scaled = scale_image(canvas, IMAGE_SCALE)
    file_name = FILE_NAME_FORMAT.format(timestamp=datetime.now(timezone.utc).timestamp())

    with io.BytesIO() as byte_stream:
        canvas_scaled.save(byte_stream, format='PNG')
        byte_stream.seek(0)
        canvas_discord_file = discord.File(byte_stream, filename=file_name)
