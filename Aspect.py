import datetime
import os
import traceback
from functools import reduce

import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from time import perf_counter

from cogs.reddit import SubredditLinker
from config import DISCORD_TOKEN

bot = commands.Bot(command_prefix='$', description="actually put something useful here eventually...",
                   activity=discord.Activity(type=discord.ActivityType.watching, name="ETH go to the moon"))


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user.name} id:{bot.user.id} at {datetime.now()}')
    subr: SubredditLinker = SubredditLinker(bot=bot)


def load_cog(ext: str) -> int:
    try:
        tick = perf_counter()
        bot.load_extension(ext)
        tock = perf_counter()
        print(f'Loaded {ext[5:]: <{reduce(max, map(len, os.listdir("./cogs"))) - 3}}in {(tock - tick):.5f}s')
        return 1
    except Exception:
        print(f"Failed to load {ext}")
        traceback.print_exc()
        return 0


extensions = ['cogs.' + filename[:-3] for filename in os.listdir("./cogs") if filename.endswith(".py")]

print(f"Successfully loaded {sum([load_cog(ext) for ext in extensions])} out of {len(extensions)} extensions")

bot.run(DISCORD_TOKEN)
