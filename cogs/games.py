import random
from discord.ext import commands
from statistics import fmean, pstdev
from typing import List
import json


def get_stats(rolls: List[int]) -> (float, float, int):
    mean = fmean(data=rolls)
    pop_stdev = pstdev(data=rolls, mu=mean)
    return mean, pop_stdev, sum(rolls)


class Games(commands.Cog, name="Games"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx: commands.Context, query: str):
        try:
            split_query = query.split("d")
            first = int(split_query[0])
            second = int(split_query[1])
            numbers = [random.randrange(second) for _ in range(first)]
            mean, stdev, sum = get_stats(numbers)
            await ctx.send(
                f'`{" ".join([str(x) for x in numbers])}\nsum: {sum}\taverage: {mean: .2f}\tstdev: {stdev: .2f}`')
        except Exception:
            await ctx.send("Invalid input! Try something like `3d20`")

    @commands.command(aliases=["randchamps", "champs"])
    async def random_champ(self, ctx: commands.Context, num_champs: int = 1):
        with open("./data/league_champions.json", encoding='UTF-8') as f:
            champion_json = json.load(f)
        champions = list(champion_json['data'].keys())
        random.shuffle(champions)
        newline = "\n"
        await ctx.send(f'{newline.join(champions[:num_champs])}')


def setup(bot):
    bot.add_cog(Games(bot))