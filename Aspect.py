from discord.ext import commands
import discord

from config import DISCORD_TOKEN
import datetime

bot = commands.Bot(command_prefix='$', description="actually put something useful here eventually...")


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user.name} id:{bot.user.id} at {datetime.datetime.now()}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="cat girls"))


extensions = ['cogs.' + cog_name for cog_name in [
    'meta',
    'reddit',
    'voice'
]]

[bot.load_extension(ext) for ext in extensions]

bot.run(DISCORD_TOKEN)
