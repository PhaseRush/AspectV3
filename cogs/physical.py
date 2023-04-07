import datetime
import os
import time

import discord
from discord.ext import commands
import shutil
import requests


def weather_endpoint(city: str):
    return f"https://v2.wttr.in/{city}.png"


class Physical(commands.Cog, name="Physicality"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["w"])
    async def weather(self, ctx: commands.Context, city='yvr'):
        response = requests.get(url=weather_endpoint(city),
                                stream=True)

        if response.status_code != 200:
            await ctx.send("Invalid city. Please try again.")
            return

        cache_path = f'./cache/weather/{city}/'
        filename = f'{time.time()}.png'
        full_path = os.path.join(cache_path, filename)

        if not os.path.exists(cache_path):
            os.makedirs(cache_path)

        with open(full_path, 'wb') as cache_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, cache_file)

        await ctx.send(file=discord.File(full_path))


def setup(bot):
    bot.add_cog(Physical(bot))
