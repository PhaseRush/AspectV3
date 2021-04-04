import ccxt
import json

from ccxt.base.errors import BadSymbol, RateLimitExceeded
import os

import uuid
from math import sqrt
from statistics import fmean, pstdev
from typing import List

from discord.ext import commands
import datetime
import asyncio
import re

from config import KRAKEN_API_KEY, KRAKEN_API_PRIVATE_KEY

FIAT_SET = {
    "USD", "CAD", "GBP", "EUR"
}


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
        print("ETH/CAD", json.dumps(self.kraken.fetch_ticker("ETH/CAD")["close"], indent=1))

    def get_price(self, origin: str, target: str) -> float:
        if origin == target:
            return 1.0
        if origin in FIAT_SET:
            return 1.0 / self.get_price(target, origin)
        price: float
        common_currency = "USD" if "USD" not in {origin, target} else "CAD"
        try:
            price = self.kraken.fetch_ticker(f"{origin}/{target}")["close"]
        except BadSymbol:
            print("Invalid ticker:", origin, target)
            # attempt to fix
            try:
                origin_to_common = self.get_price(origin, common_currency)
                try:
                    common_to_target = self.get_price(common_currency, target)
                except BadSymbol:  # probably in USD/LTC-esque loop
                    common_to_target = 1.0 / self.get_price(target, common_currency)
                print(origin_to_common, common_to_target)

                price = origin_to_common * common_to_target
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
            await ctx.send(f"{ticker}:\t{'{:.15f}'.format(self.get_price(origin, target))}")
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(aliases=["port", "value"])
    async def portfolio(self, ctx: commands.Context, *, args: str):
        portfolio: int = self.user_profiles.get(ctx.author.id, {})
        print(args)
        args: List[str] = re.split("\\s+", args)
        command: str = args[0]
        if len(args) == 0:
            # show port
            pass
        elif command in {"update", "replace"}:
            # validate input todo
            # replace dict
            self.user_profiles[ctx.author.id] =
            pass
        elif command == "value":
            # calc value
            pass


def setup(bot):
    bot.add_cog(Crypto(bot))
