import datetime
import urllib.parse

import discord
import requests
from PIL import Image
from io import BytesIO
import re
import wolframalpha
from discord.ext import commands

from config import WOLFRAM_ALPHA_APP_ID


def submission_to_embed(res) -> discord.Embed:
    return discord.Embed(
        title="Wolfram Alpha",
        url="temp url",
        # timestamp=datetime.fromtimestamp(),
        colour=discord.Colour.orange()
    ) \
        .set_image(url=res.url) \
        .set_author(name=res.author.name, url="http://google.com", icon_url=res.author.icon_img) \
        .set_footer(text="footer text", icon_url="http://youtube.com")


class Wolfram:
    def __init__(self):
        self.apikey = WOLFRAM_ALPHA_APP_ID
        self.endpoint = "https://api.wolframalpha.com/v1/simple?"

    def query(self, query_str: str):
        # url_encoded: str = urllib.parse.quote(query_str)
        payload: dict = {
            'appid': self.apikey,
            'i': query_str,
            'background': '2C2F33',  # discord dark theme background colour
            'foreground': 'white',
            'width': '800',
            'fontsize': '22',
            'units': 'metric'
        }
        response = requests.get(self.endpoint, params=payload)
        image_response = Image.open(BytesIO(response.content))
        file_name = re.sub('[^0-9a-zA-Z]+', '_', query_str)
        image_response.save(f"./cache/{file_name}.png")
        return file_name


class WolframCog(commands.Cog, name="Voice"):
    def __init__(self, bot):
        self.bot = bot
        self.client = Wolfram()

    @commands.command(aliases=["_", "__"])
    async def wolf(self, ctx: commands.Context, *query):
        file_name = self.client.query(' '.join(query))
        try:
            file = discord.File(f"./cache/{file_name}.png")
            embed = discord.Embed(title="Wolfram Alpha",
                                  colour=discord.Colour.orange(),
                                  timestamp=datetime.datetime.utcnow())
            embed.set_image(url=f"attachment://{file_name}.png")
            await ctx.send(embed=embed, file=file)
        except Exception as e:
            print(str(e))
            await ctx.send("Unable to perform wolfram query.")


def setup(bot):
    bot.add_cog(WolframCog(bot))
