import datetime
import os
import traceback

import discord
from discord.ext import commands

from config import DISCORD_TOKEN

bot = commands.Bot(command_prefix='$', description="actually put something useful here eventually...",
                   activity=discord.Activity(type=discord.ActivityType.watching, name="cat girls"))


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user.name} id:{bot.user.id} at {datetime.datetime.now()}')


def load_cog(ext: str) -> int:
    try:
        bot.load_extension(ext)
        print(f"Successfully loaded extension: {ext}")
        return 1
    except Exception:
        print(f"Failed to load {ext}")
        traceback.print_exc()
        return 0


extensions = ['cogs.' + filename[:-3] for filename in os.listdir("./cogs") if filename.endswith(".py")]

print(f"Successfully loaded {sum([load_cog(ext) for ext in extensions])} out of {len(extensions)} extensions")

bot.run(DISCORD_TOKEN)
