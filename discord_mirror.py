import time
from pathlib import Path

import discord.ext.commands
import PIL.Image


EMBED_TITLE = 'Pixels State'
EMBED_FOOTER = 'Last updated • Today at %H:%M'
IGNORED_FOLDER = Path('imgs') / 'upscale'


class MirrorBot(discord.ext.commands.Bot):
    def __init__(self, channel_id: int, message_id: int, canvas_size: dict, *args, **kwargs):
        super().__init__(command_prefix='pixels.', *args, **kwargs)
        self.channel_id = channel_id
        self.message_id = message_id
        self.canvas_size = canvas_size

    @staticmethod
    async def create_canvas_mirror(discord_channel: discord.TextChannel) -> discord.Message:
        embed = discord.Embed(title=EMBED_TITLE)
        mirror_message = await discord_channel.send(embed=embed)
        return mirror_message

    async def update_canvas_mirror(self, canvas_bytes: bytes, discord_message: discord.Message):
        canvas_pil = PIL.Image.frombytes(
            'RGB',
            (self.canvas_size['width'], self.canvas_size['height']),
            canvas_bytes
        )
        save_path = IGNORED_FOLDER / 'canvas-discord-upload.png'
        canvas_pil.save(save_path)

        embed = discord.Embed(title=EMBED_TITLE)
        embed.set_image(url=f'attachment://{save_path}')
        embed_footer = time.strftime(EMBED_FOOTER)
        embed.set_footer(text=embed_footer)

        await discord_message.edit(embed=embed)

    async def update_mirror_from_id(self, canvas_bytes: bytes):
        if not self.channel_id or not self.message_id:
            return

        channel = self.get_channel(self.channel_id)
        message = await channel.fetch_message(self.message_id)
        await self.update_canvas_mirror(canvas_bytes, message)
