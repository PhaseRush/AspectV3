import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List

import discord
from discord.ext import commands
import datetime
import asyncio

from Utils import timeit


def get_stats(ping_list: List[float]) -> (float, float):
    mean = fmean(data=ping_list)
    pop_stdev = pstdev(data=ping_list, mu=mean)
    return mean, pop_stdev


async def find_ping(ctx: commands.Context, latest_msg: discord.Message) -> (float, float, float):
    gateway_ping_diff: datetime.timedelta = datetime.datetime.utcnow() - latest_msg.edited_at
    current_time = datetime.datetime.utcnow()
    await latest_msg.edit(content=f"Testing ping, {uuid.uuid4()}")
    api_ping_diff: datetime.timedelta = latest_msg.edited_at - current_time
    gateway_ping = gateway_ping_diff.total_seconds() * 1000
    api_ping = api_ping_diff.total_seconds() * 1000
    websocket_latency = ctx.bot.latency * 1000
    return websocket_latency, gateway_ping, api_ping


class MetaCog(commands.Cog, name="Meta"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @timeit
    async def ping(self, ctx: commands.Context, sample_size: int = 3):
        websocket_latencies = []
        gateway_pings = []
        api_pings = []
        msg = await ctx.send("Checking ping..")
        for n in range(sample_size):
            await msg.edit(content="Checking ping....")
            (websocket_latency, gateway_ping, api_ping) = await find_ping(ctx, msg)
            websocket_latencies.append(websocket_latency)
            gateway_pings.append(gateway_ping)
            api_pings.append(api_ping)

            websocket_mean, websocket_dev = get_stats(websocket_latencies)
            gateway_mean, gateway_dev = get_stats(gateway_pings)
            api_mean, api_dev = get_stats(api_pings)

            await msg.edit(content=f"Checking ping...```\n"
                                   f"Iteration: {n + 1}/{sample_size}\n"
                                   f"Websocket Latency: {websocket_mean: .3f} +- {websocket_dev: .3f}ms\n"
                                   f"Gateway Ping: {gateway_mean: .3f} +- {gateway_dev: .3f}ms\n"
                                   f"Api Ping: {api_mean: .3f} +- {api_dev: .3f}ms\n"
                                   f"Total ping: {(websocket_mean + gateway_mean + api_mean): .3f} +- "
                                   f"{sqrt(websocket_dev ** 2 + gateway_dev ** 2 + api_dev ** 2): .3f}ms```")
            await asyncio.sleep(3)

    @commands.is_owner()
    async def eval(self, ctx, expr):
        await ctx.send(eval(expr))


def setup(bot):
    bot.add_cog(MetaCog(bot))
