from discord.ext import commands
import datetime


class MetaCog(commands.Cog, name="Meta"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        gateway_ping_diff: datetime.timedelta = datetime.datetime.utcnow() - ctx.message.created_at
        current_time = datetime.datetime.utcnow()
        msg = await ctx.send("ping: api test")
        api_ping_diff: datetime.timedelta = msg.created_at - current_time
        gateway_ping = gateway_ping_diff.total_seconds() * 1000
        api_ping = api_ping_diff.total_seconds() * 1000
        websocket_latency = ctx.bot.latency * 1000
        await msg.edit(
            content=f"```\nWebSocket Latency: {websocket_latency : .3f}ms\n"
                    f"Gateway Ping: {gateway_ping: .3f}ms\n"
                    f"Api Ping: {api_ping: .3f}ms\n"
                    f"Total ping: {(websocket_latency + gateway_ping + api_ping): .3f}ms```")

    @commands.is_owner()
    async def eval(self, ctx, expr):
        await ctx.send(eval(expr))


def setup(bot):
    bot.add_cog(MetaCog(bot))
