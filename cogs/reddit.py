from datetime import datetime
from typing import List

import discord
import praw
from discord.ext import commands
from praw.models import ListingGenerator, Submission

from Utils import timeit, Scheduler
from config import REDDIT_CLIENT, REDDIT_SECRET, REDDIT_ACCOUNT_PW, REDDIT_ACCOUNT_IG

reddit = praw.Reddit(client_id=REDDIT_CLIENT, client_secret=REDDIT_SECRET,
                     password=REDDIT_ACCOUNT_PW,
                     user_agent=f"Aspect:com.github.PhaseRush.Aspect:v3.0 (by /u/{REDDIT_ACCOUNT_IG})",
                     username=REDDIT_ACCOUNT_IG)


def submission_to_embed(submission: Submission) -> discord.Embed:
    return discord.Embed(
        title=submission.title,
        url=submission.url,
        timestamp=datetime.fromtimestamp(submission.created_utc),
        colour=discord.Colour.gold()
    ) \
        .set_image(url=submission.url) \
        .set_author(name=submission.author.name, url="http://google.com", icon_url=submission.author.icon_img) \
        .set_footer(text="footer text", icon_url="http://youtube.com")


class Redditor(commands.Cog, name='Reddit'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['nudes'])
    @timeit
    async def sub(self, ctx, subreddit_name: str, index: int = 0) -> None:
        subreddit: ListingGenerator = reddit.subreddit(subreddit_name).new(limit=index + 1)
        idx = 0
        for submission in subreddit:
            if idx == index:
                await ctx.send(embed=submission_to_embed(submission))
            else:
                idx += 1

    @sub.error
    async def sub_error_handler(self, ctx, error):
        print(error)
        await ctx.send(f"There's been an error!\n{error}")


class SubredditLinker(commands.Cog, name='SubredditLinker'):
    def __init__(self, bot):
        self.bot = bot
        self.subreddit_name: str = "bapcsalescanada"
        self.channel_id: str = "746506421775892521"
        self.latest_post_url: str = ""
        self.scheduler: Scheduler = Scheduler(1, self.mirror)
        self.scheduler.start()

    def find_latest_posts(self) -> List[reddit.submission]:
        subreddit: ListingGenerator = reddit.subreddit(self.subreddit_name).new(3)
        if self.latest_post_url == "":  # first time running
            return list(subreddit)
        else:
            to_post = []
            for submission in subreddit:
                if submission.url == self.latest_post_url:
                    break
                else:
                    to_post.append(submission)
            return to_post

    async def mirror(self):
        # print("mirror called")
        channel: discord.abc.GuildChannel = self.bot.get_channel(channel_id=self.channel_id)
        submissions = self.find_latest_posts()
        while submissions:
            sub = submissions.pop()
            await channel.send(embed=submission_to_embed(sub))
            self.latest_post_url = sub.url


def setup(bot):
    bot.add_cog(Redditor(bot))
    # bot.add_cog(SubredditLinker(bot))
