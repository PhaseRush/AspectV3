import importlib
import sys
import os
import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List

import discord
from discord.ext import commands
import datetime
import asyncio

import inspect

import subprocess

from Utils import timeit
from Aspect import start_time


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

    @commands.is_owner()
    @commands.command(aliases=["reboot", "gitpull"])
    async def reload(self, ctx):
        pull_result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, text=True).stdout
        if pull_result == "Already up to date.\n":
            await ctx.send("Nothing to update, " + pull_result)
            return
        await ctx.send("Reloading ...")
        subprocess.run(["python", "Aspect.py"])
        sys.exit(4)

    @commands.is_owner()
    @commands.command()
    async def git(self, ctx: commands.Context, sub_cmd: str = "status"):
        command_result = subprocess.run(["git", sub_cmd], stdout=subprocess.PIPE, text=True).stdout
        if command_result == "":
            await ctx.send("*no output*")
        else:
            await ctx.send(command_result)

    # thanks willy :)
    @commands.command()
    async def source(self, ctx, *, command: str = None):
        """Displays  source code or for a specific command.
        To display the source code of a subcommand you can separate it by
        periods or space eg. highlight.mention or highlight mention
        """
        url = 'https://github.com/Phaserush/Aspectv3'
        branch = 'master'
        if command is None:
            return await ctx.send(url)

        if len(command.split()) == 1:
            cmd = self.bot.get_command(command.replace('.', ' '))
        else:
            cmd = self.bot.get_command(command)

        if cmd is None:
            return await ctx.send('Sorry. I am unable to find that command.')

        src = cmd.callback.__code__
        module = cmd.callback.__module__
        file = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(file).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            url = 'https://github.com/Rapptz/discord.py'

        final_url = f'<{url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.send(f"{final_url}\n```py\n{''.join(lines)}\n```")

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        await ctx.send(f"Bot has been online since {start_time}\nUptime:{str(datetime.datetime.utcnow() - start_time)}")


def setup(bot):
    bot.add_cog(MetaCog(bot))
