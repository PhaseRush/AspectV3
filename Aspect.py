import codecs
import datetime
import os
import sys
import traceback
from datetime import datetime
import time
from time import perf_counter
import subprocess

import discord
from discord.ext import commands, tasks

from cogs.reddit import SubredditLinker
from config import DISCORD_TOKEN

import logging

dir = os.path.dirname(__file__)

logging.root.handlers = []
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[
                        # logging.FileHandler(f"./logs/debug-{int(time.time())}.log", "w", "utf-8"),
                        logging.FileHandler(os.path.join(dir, "logs", f"debug-{int(time.time())}.log"), "w", "utf-8"),
                        logging.StreamHandler(sys.stdout)
                    ])

logging.info(f"Starting Aspect at {datetime.utcnow()}")


class Aspect(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='$', description="actually put something useful here eventually...",
                         activity=discord.Activity(type=discord.ActivityType.watching, name=" my scripts load..."),
                         intents=discord.Intents.default(), self_bot=False)
        self.start_time = datetime.utcnow()


bot = Aspect()


@bot.event
async def on_ready():
    logging.info(f'Logged on as {bot.user.name} id:{bot.user.id} at {datetime.now()}')
    subr: SubredditLinker = SubredditLinker(bot=bot)
    # determine if we need to send reboot confirmation
    logging.info(sys.argv)
    if len(sys.argv) > 1:
        if len(sys.argv[1]) > len("reboot") and sys.argv[1].startswith("reboot"):
            prev_channel = bot.get_channel(id=int(sys.argv[1][len("reboot"):]))
            logging.info(int(sys.argv[1][len("reboot"):]))
            curr_hash = subprocess.run(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, text=True).stdout
            await prev_channel.send(f"Aspect updated to ver: {curr_hash}")
        elif sys.argv[1] == "reboot":
            prev_channel = bot.get_channel(id=int(sys.argv[1][len("reboot"):]))
            await prev_channel.send(f"Aspect rebooted.")


@bot.before_invoke
async def command_log(ctx: commands.Context):
    logging.info(f"{ctx.author} {ctx.message.content} {ctx.message}")

cogs_dir = os.path.join(dir, "cogs")

def load_cog(ext: str) -> int:
    try:
        tick = perf_counter()
        bot.load_extension(ext)
        tock = perf_counter()
        logging.info(
            f'Loaded {ext[5:]: <{max([len(file) for file in os.listdir(cogs_dir)]) - 3}} in {(tock - tick):.5f}s')
        return 1
    except Exception:
        logging.info(f"Failed to load {ext}")
        traceback.print_exc()
        return 0


extensions = ['cogs.' + filename[:-3] for filename in os.listdir(cogs_dir) if filename.endswith(".py")]

logging.info(f"Successfully loaded {sum([load_cog(ext) for ext in extensions])} out of {len(extensions)} extensions")

bot.run(DISCORD_TOKEN)
