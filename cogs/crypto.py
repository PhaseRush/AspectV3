import datetime
import json
import logging
import random
import re
import time
from collections import defaultdict
from typing import List

import urllib.request

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
OFFLINE_THRESHOLD_SECONDS = 30 * 60


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

        self.eth_activity_updater.start()

    @tasks.loop(minutes=3)
    async def eth_activity_updater(self):
        cad, _ = self.get_price("ETH", "CAD")
        usd, _ = self.get_price("ETH", "USD")
        logging.info(f"Ran eth activity loop, {cad:.2f} {usd:.2f}")
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                                 name=f"{cad:.2f} CAD / {usd:.2f} USD"))

    @eth_activity_updater.before_loop
    async def before_activity_update(self):
        await self.bot.wait_until_ready()

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
                logging.info(origin_to_common_price, common_to_target_price)

                price = (origin_to_common_price * common_to_target_price, origin_to_common_change)
            except Exception as e:
                logging.info("Failed auto fix", origin, target, e)
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
