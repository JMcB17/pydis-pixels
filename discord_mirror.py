import io
import time

import discord.ext.commands
import PIL.Image


EMBED_TITLE = 'Pixels State'
EMBED_FOOTER = 'Last updated • Today at %H:%M'
IMAGE_SCALE = 5


class MirrorBot(discord.ext.commands.Bot):
    def __init__(self, channel_id: int, message_id: int, canvas_size: dict, *args, **kwargs):
        super().__init__(command_prefix='pixels.', *args, **kwargs)
        self.channel_id = channel_id
        self.message_id = message_id
        self.canvas_size = canvas_size

        # noinspection PyTypeChecker
        self.add_command(self.startmirror)

    @staticmethod
    async def create_canvas_mirror(discord_channel: discord.TextChannel) -> discord.Message:
        embed = discord.Embed(title=EMBED_TITLE)
        mirror_message = await discord_channel.send(embed=embed)
        return mirror_message

    @discord.ext.commands.command()
    async def startmirror(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel):
        message = await self.create_canvas_mirror(channel)
        await ctx.send(f'Done, message ID: {message.id}, channel ID: {channel.id}')

    async def update_canvas_mirror(self, canvas_bytes: bytes, discord_message: discord.Message):
        canvas_pil = PIL.Image.frombytes(
            'RGB',
            (self.canvas_size['width'], self.canvas_size['height']),
            canvas_bytes)
        canvas_pil = canvas_pil.resize(
            (self.canvas_size['width'] * IMAGE_SCALE, self.canvas_size['height'] * IMAGE_SCALE),
            resample=PIL.Image.NEAREST
        )
        with io.BytesIO() as byte_stream:
            canvas_pil.save(byte_stream, format='PNG')
            byte_stream.seek(0)
            canvas_discord_file = discord.File(byte_stream, filename='canvas.png')
            uploaded = await discord_message.channel.send(file=canvas_discord_file)
            uploaded_image = uploaded.attachments[0].url
            await uploaded.delete()

        embed = discord_message.embeds[0]
        embed.set_image(url=uploaded_image)
        embed_footer = time.strftime(EMBED_FOOTER)
        embed.set_footer(text=embed_footer)

        await discord_message.edit(embed=embed)

    async def update_mirror_from_id(self, canvas_bytes: bytes):
        if not self.channel_id or not self.message_id:
            return

        channel = self.get_channel(self.channel_id)
        message = await channel.fetch_message(self.message_id)
        await self.update_canvas_mirror(canvas_bytes, message)
