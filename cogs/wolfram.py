import discord
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


class WolframCog(commands.Cog, name="Voice"):
    def __init__(self, bot):
        self.bot = bot
        self.wolfram = wolframalpha.Client(WOLFRAM_ALPHA_APP_ID)

    @commands.command(aliases=["_", "__"])
    async def wolf(self, ctx: commands.Context, args):
        res = self.wolfram.query(args)
        texts = next(res.results).text
        # await ctx.send(embed=)
        await ctx.send(content=texts)


def setup(bot):
    bot.add_cog(WolframCog(bot))
