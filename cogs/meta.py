import asyncio
import copy
import datetime
import inspect
import os
import subprocess
import sys
import time
import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List
import logging

import discord
from discord.ext import commands

from Utils import timeit, escape_md


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


# thanks willy :)
async def copy_context(src_ctx: commands.Context, *, author=None, channel=None, **kwargs):
    """
    Makes a new :class:`Context` with changed message properties.
    """
    # copy the message and update the attributes
    alt_message: discord.Message = copy.copy(src_ctx.message)
    alt_message._update(kwargs)

    if author is not None:
        alt_message.author = author
    if channel is not None:
        alt_message.channel = channel

    # obtain and return a context of the same type
    return await src_ctx.bot.get_context(alt_message, cls=type(src_ctx))


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
    @commands.command(aliases=["restart"])
    async def reboot(self, ctx: commands.Context, options: str = None):
        mode = "reboot"
        if options in {"update", "git pull"}:
            await self.git(ctx, "pull")
            mode = "update"
        mode += str(ctx.channel.id or ctx.author.id)
        logging.info(mode)
        os.execv(sys.executable, ['python'] + sys.argv + [mode])

    @commands.is_owner()
    @commands.command()
    async def git(self, ctx: commands.Context, *sub_cmd: str):
        command_result = subprocess.run(["git"] + list(sub_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True)
        stdout = command_result.stdout
        stderr = command_result.stderr  # did yall know that `git fetch` outputs only to stderr? https://github.com/git/git/blob/bf949ade81106fbda068c1fdb2c6fd1cb1babe7e/builtin/fetch.c
        msg: str = "```No output```"
        if stdout and stderr:
            if len(stdout) + len(stderr) > 1950:
                stdout = stdout[:950] + "\n..."
                stderr = stderr[:950] + "\n..."
            msg = f"stdout:```\n{escape_md(stdout)}```\n" \
                  f"stderr:```\n{escape_md(stderr)}```"
        elif stdout:
            if len(stdout) > 1950:
                stdout = stdout[1950:] + "\n..."
            msg = f"stdout:```\n{escape_md(stdout)}```"
        elif stderr:
            if len(stderr) > 1950:
                stderr = stderr[1950:] + "\n..."
            msg = f"stderr:```\n{escape_md(stderr)}```"
        try:
            await ctx.send(msg or "*No output*")
        except Exception as e:
            await ctx.send(str(e))

    # thanks willy :)
    @commands.command()
    async def source(self, ctx, *, command: str = None):
        """Displays  source code or for a specific command.
        To display the source code of a subcommand you can separate it by
        periods or space eg. highlight.mention or highlight mention
        """
        url = 'https://github.com/Phaserush/Aspectv3'
        try:
            git_branch_stdout = subprocess.run(["git", "branch"], stdout=subprocess.PIPE, text=True).stdout.split("\n")
            branch = [branch for branch in git_branch_stdout if "* " in branch][0][2:]
        except Exception:
            branch = "master"

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
        await ctx.send(f"{final_url}\n```py\n"
                       f"{escape_md(''.join(lines))}```")

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        await ctx.send(
            f"Bot has been online since {self.bot.start_time}\n"
            f"Uptime:\t{str(datetime.datetime.utcnow() - self.bot.start_time)}")

    # thanks willy again :)
    @commands.command()
    async def time(self, ctx: commands.Context, *, command_string: str):
        alt_ctx = await copy_context(ctx, content=ctx.prefix + command_string)
        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')
        elif alt_ctx.command.qualified_name == 'time':
            return await ctx.send(f"no")

        start = time.perf_counter()
        await alt_ctx.command.invoke(alt_ctx)
        end = time.perf_counter()

        return await ctx.send(f'`{command_string}` finished in {end - start:.3f}s.')


def setup(bot):
    bot.add_cog(MetaCog(bot))
