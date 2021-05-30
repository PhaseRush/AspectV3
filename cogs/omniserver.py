import importlib
import sys
import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List, Optional

import discord
from discord.ext import commands
import datetime
import asyncio

import subprocess

from Utils import timeit


class OmniCog(commands.Cog, name="Meta"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def omni_backup(self, ctx: commands.Context, index: int = 0):
        if int(ctx.author) not in {264213620026638336, 399793785820676116, 211366371471130624}:
            await ctx.send("You don't have permission to run this command")
            return
        await ctx.send(
            f"Attempting to load {'most recent' if index == 0 else str(index) + ' before most recent'} backup")
        subprocess.run(["taskkill", "/im", "javaw.exe"], stdout=subprocess.PIPE, text=True)


def setup(bot):
    bot.add_cog(OmniCog(bot))
