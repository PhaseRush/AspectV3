import random
from discord.ext import commands
from statistics import fmean, pstdev
from typing import List
import json
import requests


def get_stats(rolls: List[int]) -> (float, float, int):
    mean = fmean(data=rolls)
    pop_stdev = pstdev(data=rolls, mu=mean)
    return mean, pop_stdev, sum(rolls)


class Games(commands.Cog, name="Games"):
    def __init__(self, bot):
        self.bot = bot
        self.league_champions = requests.get(
            'http://ddragon.leagueoflegends.com/cdn/11.7.1/data/en_US/champion.json').json()
        with open("./data/league_champions.json", "w+") as f:
            json.dump(self.league_champions, f, indent=4)

        self.league_skins = requests.get(
            'http://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json').json()
        with open("./data/league_skins.json", "w+") as f:
            json.dump(self.league_skins, f, indent=4)

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
        champions = list(self.league_champions['data'].keys())
        random.shuffle(champions)
        newline = "\n"
        await ctx.send(f'{newline.join(champions[:num_champs])}')


def setup(bot):
    bot.add_cog(Games(bot))
