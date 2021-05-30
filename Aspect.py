import datetime
import os
import sys
import traceback
from datetime import datetime
import time
from time import perf_counter

import discord
from discord.ext import commands

from cogs.reddit import SubredditLinker
from config import DISCORD_TOKEN

import logging

logging.root.handlers = []
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[
                        logging.FileHandler(f"./logs/debug-{int(time.time())}.log"),
                        logging.StreamHandler(sys.stdout)
                    ])


class Aspect(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='$', description="actually put something useful here eventually...",
                         activity=discord.Activity(type=discord.ActivityType.watching, name="ETH go to the moon"))
        self.start_time = datetime.utcnow()


bot = Aspect()


@bot.event
async def on_ready():
    logging.info(f'Logged on as {bot.user.name} id:{bot.user.id} at {datetime.now()}')
    subr: SubredditLinker = SubredditLinker(bot=bot)


def load_cog(ext: str) -> int:
    try:
        tick = perf_counter()
        bot.load_extension(ext)
        tock = perf_counter()
        logging.info(f'Loaded {ext[5:]: <{max([len(file) for file in os.listdir("./cogs")]) - 3}}in {(tock - tick):.5f}s')
        return 1
    except Exception:
        logging.info(f"Failed to load {ext}")
        traceback.print_exc()
        return 0


extensions = ['cogs.' + filename[:-3] for filename in os.listdir("./cogs") if filename.endswith(".py")]

logging.info(f"Successfully loaded {sum([load_cog(ext) for ext in extensions])} out of {len(extensions)} extensions")

bot.run(DISCORD_TOKEN)
