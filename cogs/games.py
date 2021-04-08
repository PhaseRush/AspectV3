import random
from discord.ext import commands


class Games(commands.Cog, name="Games"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx: commands.Context, query: str):
        try:
            split_query = query.split("d")
            first = int(split_query[0])
            second = int(split_query[1])
            numbers = [str(random.randrange(second)) for _ in range(first)]
            await ctx.send(" ".join(numbers))
        except Exception:
            await ctx.send("Invalid input! Try something like `3d5`")


def setup(bot):
    bot.add_cog(Games(bot))
