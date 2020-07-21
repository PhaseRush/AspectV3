from discord.ext import commands


class MetaCog(commands.Cog, name="Meta"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("pong uwu")

    @commands.command(aliases=['eval'])
    @commands.is_owner()
    async def _(self, ctx, expr):
        await ctx.send(eval(expr))


def setup(bot):
    bot.add_cog(MetaCog(bot))
