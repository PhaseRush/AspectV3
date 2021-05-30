import datetime
import re
from io import BytesIO

import discord
import requests
from PIL import Image
from discord.ext import commands
import logging

from config import WOLFRAM_ALPHA_APP_ID

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
            'units': 'metric',
            'layout': 'labelbar'
        }
        response = requests.get(self.endpoint, params=payload)
        image_response = Image.open(BytesIO(response.content))
        file_name = re.sub('[^0-9a-zA-Z]+', '_', query_str)
        image_response.save(f"./cache/{file_name}.png")
        give_warning = image_response.size[1] > 1000
        return file_name, give_warning


class WolframCog(commands.Cog, name="Voice"):
    def __init__(self, bot):
        self.bot = bot
        self.client = Wolfram()

    @commands.command(aliases=["_", "__"])
    async def wolfram(self, ctx: commands.Context, *query):
        file_name, give_warning = self.client.query(' '.join(query))
        try:
            file = discord.File(f"./cache/{file_name}.png")
            embed = discord.Embed(title="Wolfram Alpha",
                                  colour=discord.Colour.orange(),
                                  timestamp=datetime.datetime.utcnow(),
                                  description="Click on the image, then \"Open Original\" to see more detail." if give_warning else "")
            embed.set_image(url=f"attachment://{file_name}.png")
            await ctx.send(embed=embed, file=file)
        except Exception as e:
            logging.info(str(e))
            await ctx.send("Unable to perform wolfram query.")


def setup(bot):
    bot.add_cog(WolframCog(bot))
