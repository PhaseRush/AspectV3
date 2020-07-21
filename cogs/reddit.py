import praw
from discord.ext import commands

from Utils import timeit
from config import REDDIT_CLIENT, REDDIT_SECRET, REDDIT_ACCOUNT_PW, REDDIT_ACCOUNT_IG

reddit = praw.Reddit(client_id=REDDIT_CLIENT, client_secret=REDDIT_SECRET,
                     password=REDDIT_ACCOUNT_PW,
                     user_agent=f"Aspect:com.github.PhaseRush.Aspect:v2.0 (by /u/{REDDIT_ACCOUNT_IG})",
                     username=REDDIT_ACCOUNT_IG)


class Redditor(commands.Cog, name='Reddit'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['nudes'])
    @timeit
    async def sub(self, ctx, subreddit_name, index=0):
        subreddit = reddit.subreddit(subreddit_name).new(limit=index + 1)
        idx = 0
        for submission in subreddit:
            if idx == index:
                await ctx.send(submission.url)
            else:
                idx += 1

    @sub.error
    async def sub_error_handler(self, ctx, error):
        await ctx.send(f"There's been an error!\n{error}")


def setup(bot):
    bot.add_cog(Redditor(bot))
