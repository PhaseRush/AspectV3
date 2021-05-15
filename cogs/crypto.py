import datetime
import json
import random
import re
import time
from collections import defaultdict
from typing import List, Optional
from types import SimpleNamespace as Namespace
import copy

import urllib.request
from tabulate import tabulate

import aiohttp
import ccxt
import discord
from ccxt.base.errors import BadSymbol, RateLimitExceeded
from discord.ext import commands, tasks

import Utils
from config import KRAKEN_API_KEY, KRAKEN_API_PRIVATE_KEY

FIAT_SET = {
    "USD", "CAD", "GBP", "EUR"
}

INVALID_UPDATE_EXAMPLE = "ETH:2.091 BTC:0.0023 USD:230.01"

PORTFOLIO_UPDATE_ALIASES = {"update", "replace", "set"}
PORTFOLIO_VIEW_ALIASES = {"view", "check", "value", "show", None}  # None for default option
PORTFOLIO_CHANGE_DEFAULT_FIAT = {"default_fiat", "fiat"}


class Crypto(commands.Cog, name="Crypto"):
    def __init__(self, bot):
        self.bot = bot
        self.default_market = ccxt.bitmex()  # todo
        with open('./data/crypto_profiles.json') as f:
            self.user_profiles = json.load(f)

        with open('./data/crypto_tickers.json') as f:
            self.tickers = json.load(f)

        self.kraken = ccxt.kraken({
            'apiKey': KRAKEN_API_KEY,
            'secret': KRAKEN_API_PRIVATE_KEY,
        })
        # print("ETH/CAD", json.dumps(self.kraken.fetch_ticker("ETH/CAD")["close"], indent=1))

        with open('./data/miner_alerts.json') as f:
            self.miner_alerts = json.load(f)

        self.last_alerted = {}
        self.miner_ignore = {}
        self.miner_check.start()

        with open('./data/ethermine_addresses.json') as f:
            self.ethermine_addresses = json.load(f)

    @tasks.loop(seconds=30.0)
    async def miner_check(self):
        async with aiohttp.ClientSession() as cs:
            for address, val in self.miner_alerts.items():
                async with cs.get(f"https://api.ethermine.org/miner/:{address}/dashboard") as ethermine:
                    ethermine_json = await ethermine.json()
                    current_workers = {(item['worker'], item['lastSeen']) for item in ethermine_json['data']['workers']}
                    missing_workers = []
                    for name, last_seen in current_workers:
                        if name not in self.miner_ignore.get(val['discord_user_id'], []):
                            if name not in val['expected_miners'] or time.time() - last_seen > 30 * 60:
                                missing_workers.append(name)
                    if len(missing_workers):
                        if time.time() - self.last_alerted.get(address, 0) > val['alert_freq_sec']:
                            self.last_alerted[address] = time.time()
                            for channel in [self.bot.get_channel(channel_id) for channel_id in val['channels']]:
                                await channel.send(f"<@{val['discord_user_id']}> {','.join(missing_workers)} is down!\n"
                                                   f"https://ethermine.org/miners/{address}/dashboard")

    @miner_check.before_loop
    async def before_ready(self):
        await self.bot.wait_until_ready()

    @commands.command(aliases=["ignore"])
    async def mute_miner_alert(self, ctx, miner_name):
        if miner_name in self.miner_ignore.get(ctx.author.id, []):
            self.miner_ignore.get(ctx.author.id).remove(miner_name)
            await ctx.send(f"Removed {miner_name} from ignore list.")
        else:
            self.miner_ignore.get(ctx.author.id).append(miner_name)
            await ctx.send(f"Added {miner_name} to ignore list")

    @commands.command(aliases=["minerstat"])
    async def mining_statistics(self, ctx: commands.Context, selector: Optional[str]):
        cumulative_data = None
        data_entries = []
        addresses_to_merge = None
        async with aiohttp.ClientSession() as cs:
            if selector is None or selector == "":
                addresses_to_merge = [self.ethermine_addresses.get(str(ctx.author.id),
                                                                   self.ethermine_addresses.get(
                                                                       "264213620026638336"))]
            elif selector in {"all", "acc", "total"}:
                addresses_to_merge = self.ethermine_addresses.values()

            for addr in addresses_to_merge:
                async with cs.get(f"https://api.ethermine.org/miner/:{addr}/currentStats") as ethermine:
                    ethermine_json = json.dumps(await ethermine.json())
                    curr_data = json.loads(ethermine_json, object_hook=lambda d: Namespace(**d)).data
                    curr_data.addr = addr
                    if cumulative_data is None:
                        cumulative_data = curr_data
                        data_entries.append(copy.deepcopy(curr_data))
                    else:
                        cumulative_data.reportedHashrate += curr_data.reportedHashrate
                        cumulative_data.currentHashrate += curr_data.currentHashrate
                        cumulative_data.averageHashrate += curr_data.averageHashrate
                        cumulative_data.unpaid += curr_data.unpaid
                        cumulative_data.usdPerMin += curr_data.usdPerMin
                        data_entries.append(copy.deepcopy(curr_data))

        headers = ["Wallet", "Avg. HR", "USD/Day"]
        table = []

        for data in data_entries:
            table.append([f"{data.addr[:6]}...{data.addr[-4:]}",
                          round(data.averageHashrate / 1e6, 2),
                          round(data.usdPerMin * 60 * 24, 2)])

        if len(data_entries) > 1:
            table.append([f"Cumulative", round(cumulative_data.averageHashrate / 1e6, 2),
                          round(cumulative_data.usdPerMin * 60 * 24, 2)])

        desc = tabulate(table, headers=headers)

        embed: discord.Embed = discord.Embed(
            title=f"Ethermine report",
            description=f"```{desc}```",
            timestamp=datetime.datetime.utcnow(),
            colour=ctx.author.colour
        )
        await ctx.send(embed=embed)

    def get_price(self, origin: str, target: str) -> (float, float):
        if origin == target:
            return 1.0, 1.0
        if origin in FIAT_SET and target in FIAT_SET:  # both fiat
            try:
                if random.getrandbits(1):
                    ticker = self.kraken.fetch_ticker(f"{target}/{origin}")
                    return ticker['close'], ticker['info']['l'][1]
                else:
                    ticker = self.kraken.fetch_ticker(f"{origin}/{target}")
                    return ticker['close'], ticker['info']['l'][1]
            except BadSymbol:
                return self.get_price(target, origin)
        if origin in FIAT_SET:
            a, b = self.get_price(target, origin)
            return 1.0 / a, 1 / b

        price: (float, float)
        common_currency = "USD" if "USD" not in {origin, target} else "CAD"
        try:
            ticker = self.kraken.fetch_ticker(f"{origin}/{target}")
            price = (ticker['close'], float(ticker['info']['l'][1]))
        except BadSymbol:
            # attempt to fix invalid ticker
            try:
                origin_to_common_price, origin_to_common_change = self.get_price(origin, common_currency)
                try:
                    common_to_target_price, common_to_target_change = self.get_price(common_currency, target)
                except BadSymbol:  # probably in USD/LTC-esque loop
                    target_to_common_price, target_to_common_change = self.get_price(target, common_currency)
                    common_to_target_price = 1.0 / target_to_common_price
                print(origin_to_common_price, common_to_target_price)

                price = (origin_to_common_price * common_to_target_price, origin_to_common_change)
            except Exception as e:
                print("Failed auto fix", origin, target, e)
                raise Exception("Unsupported ticker, automatic conversion failed. Try using USD.")

        except ValueError:
            raise ValueError("Invalid ticker, use a format like: \"BTC/USD\"")

        except RateLimitExceeded:
            raise RateLimitExceeded("Rate limited. Try again later.")

        except RecursionError:
            raise RecursionError("why.")

        except Exception:
            raise Exception("Unknown error, try another ticker.")

        return price

    # noinspection PyBroadException
    @commands.command(aliases=["t", "$", "tick"])
    async def ticker_price(self, ctx: commands.Context, ticker: str):
        ticker = ticker.upper()
        (origin, target) = ticker.split("/")
        try:
            price, last_24 = self.get_price(origin, target)
            await ctx.send(f"{ticker}:\t{price: .2f}\n24 Hr {100 * price / last_24 - 100 : .2f}%")
        except Exception as e:
            await ctx.send(str(e))

    def persist_profiles(self):
        with open("./data/crypto_profiles.json", "w") as f:
            json.dump(self.user_profiles, f, indent=4)

    # noinspection PyBroadException
    @commands.command(aliases=["port", "value"])
    async def portfolio(self, ctx: commands.Context, *args: tuple):
        profile: {} = self.user_profiles.get(str(ctx.author.id), {})
        portfolio: {} = profile.get("portfolio", {})
        args: List[str] = [] if len(args) == 0 else [re.sub(r"[^a-zA-Z0-9_.:]+", "", str(arg)) for arg in args]
        command: str = args[0] if args else None  # get first or None if not exists
        if command in PORTFOLIO_VIEW_ALIASES:
            if not profile:
                await ctx.send("Your portfolio is empty. Use \"`set`\" to make your portfolio.")
            else:
                # await ctx.send(json.dumps(profile))  # todo: pretty print
                await ctx.send(embed=await self.generate_portfolio_embed(ctx, portfolio))
        elif command in PORTFOLIO_UPDATE_ALIASES:
            currencies = {}
            try:
                for entry in args[1:]:  # skip first entry since it is a command
                    currency, amount = entry.split(":")
                    if currency in self.tickers.keys() | FIAT_SET:  # union crypto and fiat symbols
                        currencies[currency] = float(amount)

                profile["portfolio"] = currencies
                self.user_profiles[str(ctx.author.id)] = profile
                self.persist_profiles()
                await ctx.send("Portfolio updated.")
            except Exception:
                await ctx.send(
                    "Sorry, invalid input. Use this as an example:\n`$port set " + INVALID_UPDATE_EXAMPLE + "`")

        elif command in PORTFOLIO_CHANGE_DEFAULT_FIAT:
            desired = args[1].upper()
            if desired not in FIAT_SET:
                await ctx.send("Sorry, your fiat currency must be one of " + ",".join(FIAT_SET))
                return
            self.user_profiles[str(ctx.author.id)]["default_fiat"] = desired
            self.persist_profiles()
            await ctx.send("Default fiat currency updated to " + desired)
        else:
            await ctx.send(f"""
            Invalid command. Try again using one of the commands below:
            Your portfolio's value:\t{",".join(PORTFOLIO_VIEW_ALIASES)}
            Update your portfolio:\t{",".join(PORTFOLIO_UPDATE_ALIASES)}
            """)

    async def generate_mobile_embed(self, ctx: commands.Context, portfolio: dict) -> discord.Embed:
        target_fiat = self.user_profiles.get(str(ctx.author.id), {}).get("default_fiat", "USD")

        values = {ticker: (self.get_price(ticker, target_fiat), amount) for ticker, amount in portfolio.items()}
        values = {ticker: (pair_amount[0][0] * pair_amount[1], pair_amount[0][1]) for ticker, pair_amount in
                  values.items()}
        values = dict(reversed(sorted(values.items(), key=lambda entry: entry[1])))
        calculated = Utils.merge_dicts(portfolio, values)
        desc = f"{'Currency': <12}{'Quantity': ^12}{'Value (' + target_fiat + ')': ^12}{'24 hr': ^8}\n" + \
               "\n".join(
                   [f"{ticker: ^10}{value[0]: >12}{value[1]: >12.2f}{100 * self.determine_change(value) - 100: >8.2f}%"
                    for
                    ticker, value in
                    calculated.items()]) + \
               f"\n{'-' * 43}" + \
               f"\n{'Total value': <18}{sum([x[0] for x in values.values()]): >16.2f}"

        quote_symbol = "'"
        quote_symbol_s = "'s"
        name = ctx.author.nick or ctx.author.name
        embed: discord.Embed = discord.Embed(
            title=f"{name}{quote_symbol if name[-1].lower() == 's' else quote_symbol_s} Portfolio",
            description=f"```\n{desc}\n```",
            timestamp=datetime.datetime.utcnow(),
            colour=ctx.author.colour
        )

        return embed

    async def generate_desktop_embed(self, ctx: commands.Context, portfolio: dict) -> discord.Embed:
        pass

    async def generate_portfolio_embed(self, ctx: commands.Context, portfolio: dict) -> discord.Embed:
        # return await self.generate_mobile_embed(ctx, portfolio) if ctx.author.is_on_mobile() else await self.generate_desktop_embed(
        #     ctx, portfolio)
        return await self.generate_mobile_embed(ctx, portfolio)

    def determine_change(self, values: List):
        return values[1] / values[0] / values[2]


def setup(bot):
    bot.add_cog(Crypto(bot))
