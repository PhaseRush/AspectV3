import datetime
from typing import List

import discord

import os
import matplotlib as mpl

if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from discord.ext import commands


def format_large_number(num: float) -> str:
    if num < 100000:
        return str(num)
    elif num > 1e15:
        return f"{(num // 10e9) / 100}T"
    elif num > 1e9:
        return f"{(num // 10e6) / 100}B"
    elif num > 1e6:
        return f"{(num // 10e3) / 100}M"
    else:
        return str(num)


substitutions = {
    "xeqt": "xeqt.to",
    "appl": "aapl",
    "novideo": "nvda",
    "jeff": "amzn",
    "shintel": "intc"
}

valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]  # actually, any 'd' works
valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]

interval_period_link = {
    "1d": "15m",
    "1mo": "1d",
    "3mo": "1d",
    "6mo": "1wk",
    "1y": "1wk",
    "2y": "1mo",
    "5y": "3mo",
    "10y": "3mo",
    "ytd": "1mo",
    "max": "1yr"
}


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
        print(fast)

        last_price = fast.last_price
        change_absolute = last_price - fast.previous_close
        change_percent = 100 * change_absolute / fast.previous_close

        day_range = f"{fast.day_low: .2f}-{fast.day_high: .2f}"
        fiftytwo_week_range = f"{fast.year_low: .2f}-{fast.year_high: .2f} ({(100 * fast.year_change):+.2f})"

        try:
            market_cap = format_large_number(fast.market_cap)
        except:
            market_cap = ""

        try:
            trailing_pe = info.info['trailingPE']
        except:
            trailing_pe = -1

        try:
            data_formatted = pd.DataFrame.from_dict(info.info, orient='index')
            trailing_eps = data_formatted.at['trailingEps', 0]
            if trailing_eps is None:
                trailing_eps = -1
        except:
            trailing_eps = -1

        # f"{'Beta (5Y Monthly)': <15}{info.info['beta']: >25}\n" + \
        desc: str = f"{'Prev. close': <15}{round(fast.previous_close, 2): >25}\n" + \
                    f"{'Open': <15}{round(fast.open, 2): >25}\n" + \
                    f"{'Days range': <15}{day_range: >25}\n" + \
                    f"{'52 week range': <15}{fiftytwo_week_range: >25}\n" + \
                    f"{'Volume': <15}{format_large_number(fast.last_volume): >25}\n" + \
                    f"{'Market cap': <15}{market_cap: >25}\n" + \
                    f"{'PE ratio(TTM)': <15}{round(trailing_pe, 2): >25}\n" + \
                    f"{'EPS (TTM)': <15}{trailing_eps: >25}\n"

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
        if len(cmd) == 1:
            await self.fetch_current_price(message, substitutions.get(cmd[0], cmd[0]), "1d", "15m")
        elif len(cmd) == 2:
            interval = cmd[1]
            if not interval.endswith('d') and interval not in valid_intervals:
                await message.channel.send("Invalid interval, please use number of days, or something from " + ' '.join(valid_intervals))
            await self.fetch_current_price(message, substitutions.get(cmd[0], cmd[0]), interval, interval_period_link.get(interval, "15m"))
        elif len(cmd) == 3:
            interval = cmd[1]
            period = cmd[2]
            if not interval.endswith('d') and interval not in valid_intervals:
                await message.channel.send("Invalid interval, please use number of days, or something from " + ' '.join(valid_intervals))
            if not period.endswith('d') and period not in valid_periods:
                await message.channel.send("Invalid period, please use number of days, or something from " + ' '.join(valid_periods))
            await self.fetch_current_price(message, substitutions.get(cmd[0], cmd[0]), interval, period)
def setup(bot):
    bot.add_cog(Finance(bot))
