import collections
from typing import List

from discord.ext import commands
from bs4 import BeautifulSoup
import pickle
import random
import logging


def parse_html(path) -> List[List[str]]:
    with open(path) as f:
        soup = BeautifulSoup(f, "html.parser")
        table = soup.find('table', attrs={'class': 'wikitable'})
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')

        table_data = []
        for row in rows:
            cols = row.find_all('td')
            table_data.append([ele for ele in cols])  # Get rid of empty values

        all_data_in_file = []
        for i, x in enumerate(table_data):
            if x:
                cleaned = []
                for idx, y in enumerate(x):
                    if idx == 0:
                        cleaned.append(y.string)
                    elif idx in (1, 2, 3, 4):
                        cleaned.append(y.a['title'])
                    elif idx in (5, 6, 7, 8):
                        lst = y.contents
                        acc = ""
                        for i in lst:
                            try:
                                acc += i.attrs['title'] + " "
                            except:
                                pass
                        cleaned.append(acc)
                    elif idx in (9, 10):
                        acc = ""
                        for i9 in y.contents:
                            try:
                                acc += i9.contents[0] + " "
                            except:
                                pass
                        cleaned.append(acc)
                    elif idx in (12, 13):
                        cleaned.append(y.contents[0]['href'])
                cleaned.append(path[:-9][-3:])
                # print(path[:-9][-3:])
                all_data_in_file.append([str(x) for x in cleaned])  # or else it saves html objects and pkl fails
        return all_data_in_file


class LeagueGuessingCog(commands.Cog, name="Guess"):
    def __init__(self, bot):
        # sys.setrecursionlimit(100000)
        self.bot = bot
        self.all_match_data = []
        try:
            self.all_match_data = pickle.load(open("data/leaguesite/all_match_data.pkl", "rb"))
        except:
            try:
                self.all_match_data += parse_html("data/leaguesite/lcs_raw.html")
                self.all_match_data += parse_html("data/leaguesite/lpl_raw.html")
                pickle.dump(self.all_match_data, open("data/leaguesite/all_match_data.pkl", "wb"))
            except:
                logging.info("Skipping league game data loading. Likely running in jail env.")
        logging.info(f"Loaded {len(self.all_match_data)} games")

    @commands.command(aliases=['g'])
    async def guess(self, ctx: commands.Context, *query):
        g = random.choice(self.all_match_data)
        r1, r2, r3 = random.sample(range(4, 15), 3)
        msg = f"""
Date and Patch: {g[0]} {g[1]}
Region: ||{g[12]}||
Matchup:
||{g[2]}: {g[9]}||
\t\t\t-- VS --
||{g[3]}: {g[10]}||

||{g[2]} {'-' * r1}||
bans: ||{g[5]}|| 
||{g[3]} {'-' * r2}||
ans: ||{g[6]}||

||{g[2]} {'-' * r1}||
picks: {g[7]}
||{g[3]} {'-' * r2}||
picks: {g[8]}

Winner: ||{'-' * r3} {g[4]} {'-' * r3} ||
VOD: ||{g[11]}||
        """
        await ctx.send(msg)

    @commands.command(aliases=['gs'])
    async def gscore(self, ctx: commands.Context, *query):
        pass

    @commands.command(aliases=['lm'])
    async def matchup(self, ctx: commands.Context, *query):
        """
        0 date
        1 patch
        2 t1
        3 t2
        4 winner
        5 t1 ban
        6 t2 ban
        7 t1 pick
        8 t2 pick
        9 t1 roster
        10 t2 roster
        11 vod link
        12 region
        """
        a_won = 0
        b_won = 0

        champ1 = query[0].lower()
        champ2 = query[1].lower()
        champ1_patches = collections.defaultdict(int)
        champ2_patches = collections.defaultdict(int)
        total_count = 0
        for g in self.all_match_data:
            if champ1 in g[7].lower() and champ2 in g[8].lower():
                total_count += 1
                if g[4] == g[2]:  # champ1 won
                    a_won += 1
                    champ1_patches[g[1]] += 1
                else:
                    b_won += 1
                    champ2_patches[g[1]] += 1
            elif champ1 in g[8].lower() and champ2 in g[7].lower():
                total_count += 1
                if g[4] == g[3]:  # champ1 won
                    a_won += 1
                    champ1_patches[g[1]] += 1
                else:
                    b_won += 1
                    champ2_patches[g[1]] += 1

        print(champ1_patches)
        await ctx.send(f"{a_won}:{b_won}\n"
                       f"Sample size: {len(self.all_match_data)}\n"
                       f"Play count: {total_count}\n"
                       f"{query[0]} patches and wins: {champ1_patches.items()}\n"
                       f"{query[1]} patches and wins: {champ2_patches.items()}")


def setup(bot):
    bot.add_cog(LeagueGuessingCog(bot))
