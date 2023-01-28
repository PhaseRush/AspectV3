import datetime
from typing import List

import discord
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from discord.ext import commands


def format_market_cap(market_cap: float) -> str:
    if market_cap > 10e12:
        return f"{(market_cap // 10e9) / 1000}T"
    elif market_cap > 10e9:
        return f"{(market_cap // 10e6) / 1000}B"
    elif market_cap > 10e6:
        return f"{(market_cap // 10e3) / 1000}M"


class Finance(commands.Cog, name="Finance"):

    def __init__(self, bot):
        self.bot = bot

    async def fetch_current_price(self,
                                  message: discord.Message,
                                  ticker: str,
                                  period: str = "2d",
                                  interval: str = "15m"):
        info = yf.Ticker(ticker)
        fast = info.fast_info

        last_price = fast.last_price
        change_absolute = last_price - fast.previous_close
        change_percent = 100 * change_absolute / fast.previous_close

        day_range = f"{fast.day_low: .2f} - {fast.day_high: .2f}"
        fiftytwo_week_range = f"{fast.year_low: .2f} - {fast.year_high: .2f} ({(100 * fast.year_change):+.2f})"
        market_cap = format_market_cap(fast.market_cap)

        data_formatted = pd.DataFrame.from_dict(info.info, orient='index')

            # f"{'Beta (5Y Monthly)': <12}{info.info['beta']: >25}\n" + \
        desc: str = f"{'Prev. close': <12}{round(fast.previous_close, 2): >25}\n" + \
                    f"{'Open': <12}{round(fast.open, 2): >25}\n" + \
                    f"{'Days range': <12}{day_range: >25}\n" + \
                    f"{'52 week range': <12}{fiftytwo_week_range: >25}\n" + \
                    f"{'Volume': <12}{fast.last_volume: >25}\n" + \
                    f"{'Market cap': <12}{market_cap: >25}\n" + \
                    f"{'PE ratio(TTM)': <12}{info.info['trailingPE']: >25}\n" + \
                    f"{'EPS (TTM)': <12}{data_formatted.at['trailingEps', 0]: >25}\n"

        data = yf.download(ticker, period=period, interval=interval)
        data.drop('Volume', axis=1, inplace=True)
        data.plot.line()
        file_name = f'./cache/{ticker}-{period}-{interval}-{message.id}.png'
        plt.savefig(file_name)

        file = discord.File(file_name)
        embed = discord.Embed(title=f"{ticker.upper()} {last_price:.2f} "
                                    f"{change_absolute:+.2f}"
                                    f" ({change_percent:+.2f}%)",
                              colour=discord.Colour.orange(),
                              timestamp=datetime.datetime.utcnow(),
                              description=f"```\n{desc}\n```",
                              url=f"https://finance.yahoo.com/quote/{ticker}/")
        embed.set_image(url=f"attachment://{file_name}.png")
        # embed.set_thumbnail(url=info.info['logo_url'])
        await message.channel.send(embed=embed, file=file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.content.startswith("$"):
            return

        cmd: List[str] = message.content[1:].split()
        match cmd:
            case [str()]:
                print("case1")
                await self.fetch_current_price(message, cmd[0], "2d", "15m")
            case [str(), str(), str()]:
                print("case2")
                await self.fetch_current_price(message, *cmd)


def setup(bot):
    bot.add_cog(Finance(bot))
