import io
import time

import discord
import discord.ext.commands
import PIL.Image


EMBED_TITLE = 'Pixels State'
EMBED_FOOTER = 'Last updated • Today at %H:%M'


async def create_canvas_mirror(discord_channel: discord.TextChannel) -> discord.Message:
    embed = discord.Embed(title=EMBED_TITLE)
    mirror_message = await discord_channel.send(embed=embed)
    return mirror_message


@discord.ext.commands.command()
async def startmirror(ctx: discord.ext.commands.Context, channel: discord.TextChannel):
    message = await create_canvas_mirror(channel)
    await ctx.send(f'Done, message ID: {message.id}')


async def update_canvas_mirror(canvas_bytes: bytes, canvas_size: dict, discord_message: discord.Message):
    canvas_pil = PIL.Image.frombytes('RGB', (canvas_size['width'], canvas_size['height']), canvas_bytes)
    with io.BytesIO() as byte_stream:
        canvas_pil.save(byte_stream, format='PNG')
        byte_stream.seek(0)
        canvas_discord_file = discord.File(byte_stream)
        uploaded = await discord_message.channel.send(file=canvas_discord_file)
        uploaded_image = uploaded.attachments[0].url
        await uploaded.delete()

    embed = discord_message.embeds[0]
    embed.set_image(uploaded_image)
    embed_footer = time.strftime(EMBED_FOOTER)
    embed.set_footer(embed_footer)

    await discord_message.edit(embed=embed)
