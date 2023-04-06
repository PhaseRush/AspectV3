import ast
import asyncio
import copy
from datetime import datetime
from pytz import timezone
import inspect
import os
import subprocess
import sys
import time
import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List, Optional, Any
import textwrap
import io
from contextlib import redirect_stdout
import traceback

import discord
from discord.ext import commands, tasks

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


def cleanup_code(content: str) -> str:
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


class MetaCog(commands.Cog, name="Meta"):
    def __init__(self, bot):
        self.bot = bot
        self._last_result: Optional[Any] = None
        self.sessions: set[int] = set()

        self.china = datetime.now(timezone('Asia/Shanghai'))
        self.china_time.start()

    @tasks.loop(seconds=10)
    async def china_time(self):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                                 name=self.china.strftime("%m/%d - %H:%M")))

    @china_time.before_loop
    async def before_activity_update(self):
        await self.bot.wait_until_ready()

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
        if len(sys.argv) >= 2:
            sys.argv[1] = mode
        else:
            sys.argv.append(mode)
        os.execv(sys.executable, ['python'] + sys.argv)

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

    @commands.command(hidden=True, name='eval')
    @commands.is_owner()
    async def _eval(self, ctx: commands.Context, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result,
        }

        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')


def setup(bot):
    bot.add_cog(MetaCog(bot))
