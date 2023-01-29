import datetime
from typing import List

import discord
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from discord.ext import commands


def format_large_number(market_cap: float) -> str:
    if market_cap > 1e15:
        return f"{(market_cap // 10e9) / 100}T"
    elif market_cap > 1e9:
        return f"{(market_cap // 10e6) / 100}B"
    elif market_cap > 1e6:
        return f"{(market_cap // 10e3) / 100}M"


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

        day_range = f"{fast.day_low: .2f}-{fast.day_high: .2f}"
        fiftytwo_week_range = f"{fast.year_low: .2f}-{fast.year_high: .2f} ({(100 * fast.year_change):+.2f})"
        market_cap = format_large_number(fast.market_cap)

        data_formatted = pd.DataFrame.from_dict(info.info, orient='index')

            # f"{'Beta (5Y Monthly)': <15}{info.info['beta']: >25}\n" + \
        desc: str = f"{'Prev. close': <15}{round(fast.previous_close, 2): >25}\n" + \
                    f"{'Open': <15}{round(fast.open, 2): >25}\n" + \
                    f"{'Days range': <15}{day_range: >25}\n" + \
                    f"{'52 week range': <15}{fiftytwo_week_range: >25}\n" + \
                    f"{'Volume': <15}{format_large_number(fast.last_volume): >25}\n" + \
                    f"{'Market cap': <15}{market_cap: >25}\n" + \
                    f"{'PE ratio(TTM)': <15}{round(info.info['trailingPE'], 2): >25}\n" + \
                    f"{'EPS (TTM)': <15}{data_formatted.at['trailingEps', 0]: >25}\n"

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
            await self.fetch_current_price(message, cmd[0], "2d", "15m")
        elif len(cmd) == 2:
            await self.fetch_current_price(message, *cmd)


def setup(bot):
    bot.add_cog(Finance(bot))
