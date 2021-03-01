import datetime
import os
import traceback

import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime

from cogs.reddit import SubredditLinker
from config import DISCORD_TOKEN

bot = commands.Bot(command_prefix='$', description="actually put something useful here eventually...",
                   activity=discord.Activity(type=discord.ActivityType.watching, name="cat girls"))


@tasks.loop(minutes=60)
async def genshin_login_reminder(self):
    if datetime.now().hour == 15:
        embed = discord.Embed(title="Daily Genshin Reminder", url="https://webstatic-sea.mihoyo.com/ys/event/signin-sea/index.html?act_id=e202102251931481&lang=en-us")
        await self.bot.get_channel("809702154725097533").send(embed=embed)


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user.name} id:{bot.user.id} at {datetime.datetime.now()}')
    genshin_login_reminder.start()
    subr: SubredditLinker = SubredditLinker(bot=bot)


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
