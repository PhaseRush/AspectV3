import importlib
import sys
import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List

import discord
from discord.ext import commands
import datetime
import asyncio

import subprocess

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
    async def hello(self, ctx: commands.Context):
        await ctx.send("hellowo")

    @commands.command()
    @timeit
    async def ping(self, ctx: commands.Context, sample_size: int = 3):
        if 0 > sample_size > 10:
            await ctx.send(content="Invalid range! Please pick a number between (0, 10)")
            return
        websocket_latencies = []
        gateway_pings = []
        api_pings = []
        msg = await ctx.send("Checking ping...")
        for n in range(sample_size):
            await msg.edit(content=f"Checking ping ... {n + 1}/{sample_size}")
            (websocket_latency, gateway_ping, api_ping) = await find_ping(ctx, msg)
            websocket_latencies.append(websocket_latency)
            gateway_pings.append(gateway_ping)
            api_pings.append(api_ping)

            websocket_mean, websocket_dev = get_stats(websocket_latencies)
            gateway_mean, gateway_dev = get_stats(gateway_pings)
            api_mean, api_dev = get_stats(api_pings)

            await msg.edit(content=f"Checking ping... {n + 1}/{sample_size}```\n"
                                   f"{'Websocket': >10}: {websocket_mean: >10.3f} ± {websocket_dev: >8.3f}ms\n"
                                   f"{'Gateway': >10}: {gateway_mean: >10.3f} ± {gateway_dev: >8.3f}ms\n"
                                   f"{'Api': >10}: {api_mean: >10.3f} ± {api_dev: >8.3f}ms\n"
                                   f"{'Total': >10}: {(websocket_mean + gateway_mean + api_mean): > 10.3f} ± "
                                   f"{sqrt(websocket_dev ** 2 + gateway_dev ** 2 + api_dev ** 2): >8.3f}ms```")
            await asyncio.sleep(3)

    @commands.is_owner()
    async def eval(self, ctx, expr):
        await ctx.send(eval(expr))

    @commands.command()
    async def reload(self, ctx):
        pull_result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, text=True)
        # subprocess.run(["git"], stdout=subprocess.PIPE, text=True, input="fetch")
        print(pull_result)
        await ctx.send(pull_result)
        sys.exit(2)


def setup(bot):
    bot.add_cog(MetaCog(bot))
