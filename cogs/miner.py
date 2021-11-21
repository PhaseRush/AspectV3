import asyncio
import json
import logging
import time

import aiohttp
import subprocess
import paramiko
import re
from discord.ext import commands, tasks

OFFLINE_THRESHOLD_SECONDS = 30 * 60

#  https://stackoverflow.com/a/14693789
ansi_escape = re.compile(r'''
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
''', re.VERBOSE)


class Miner(commands.Cog, name="Miner"):
    def __init__(self, bot):
        self.bot = bot

        with open('./data/miner_alerts.json') as g:
            self.miner_alerts = json.load(g)

        with open('./data/miner_log.json') as g:
            self.miner_log = json.load(g)

        self.last_alerted = {}
        self.miner_check.start()

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # figuring out to add this took like 5 years
        self.client.connect(self.miner_log['internal_ip'],
                            username=self.miner_log['username'],
                            password=self.miner_log['user_pw'])

        self.start_miner_output.start()

    @tasks.loop(seconds=20.0)
    async def miner_check(self):
        async with aiohttp.ClientSession() as cs:
            for address, val in self.miner_alerts.items():
                if val['mute_until'] < time.time():  # if muted, dont check
                    async with cs.get(f"https://api.ethermine.org/miner/:{address}/dashboard") as ethermine:
                        ethermine_json = await ethermine.json()
                        current_workers = {item['worker']: item['lastSeen'] for item in
                                           ethermine_json['data']['workers']}
                        missing_workers = []
                        for expected in val['expected_miners']:
                            if expected not in current_workers.keys():  # expected worker does not exist
                                missing_workers.append(expected)
                            else:
                                if time.time() - current_workers[
                                    expected] > OFFLINE_THRESHOLD_SECONDS:  # worker exists but is too old
                                    missing_workers.append(expected)

                        if len(missing_workers):
                            if time.time() - self.last_alerted.get(address, 0) > val['alert_freq_sec']:
                                self.last_alerted[address] = time.time()
                                for channel in [self.bot.get_channel(channel_id) for channel_id in val['channels']]:
                                    await channel.send(
                                        f"<@{val['discord_user_id']}> {','.join(missing_workers)} is down!\n"
                                        f"https://ethermine.org/miners/{address}/dashboard")

    @miner_check.before_loop
    async def before_ready(self):
        await self.bot.wait_until_ready()

    @commands.command()
    async def mute(self, ctx: commands.Context, duration_minutes: int):
        for address, val in self.miner_alerts.items():
            if int(val['discord_user_id']) == ctx.author.id:
                val['mute_until'] = time.time() + duration_minutes * 60
                with open('./data/miner_alerts.json', 'w', encoding='utf-8') as f:
                    json.dump(self.miner_alerts, f, indent=2)
                await ctx.send(f"Alerts for {address} have been muted for the next {duration_minutes} minutes")

    @tasks.loop(count=1)
    async def start_miner_output(self):
        stdin, stdout, stderr = self.client.exec_command("motd")
        opt = "".join(stdout.readlines())
        opt = f"```\n{ansi_escape.sub('', opt)}\n```"  # remove colour codes and put into code block
        channel = self.bot.get_channel(self.miner_log['channel_id'])
        await channel.send(opt)

    @start_miner_output.before_loop
    async def before_log(self):
        await self.bot.wait_until_ready()

    @commands.is_owner()
    @commands.command(aliases=["hive"])
    async def run_command_on_hive(self, ctx: commands.Context, cmd: str):
        stdin, stdout, stderr = self.client.exec_command(cmd)
        opt = "".join(stdout.readlines())
        opt = f"```\n{ansi_escape.sub('', opt)}\n```"  # remove colour codes and put into code block
        await ctx.send(opt)


def setup(bot):
    bot.add_cog(Miner(bot))
