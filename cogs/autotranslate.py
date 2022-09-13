import random
import time

import discord
from discord.ext import commands
import re
import deepl
import pinyin
from config import DEEPL_TOKEN


class Autotranslate(commands.Cog, name="Autotranslate"):
    def __init__(self, bot):
        self.dog_prob = 0.01
        self.bot = bot
        self.deepl = deepl.Translator(DEEPL_TOKEN)
        self.rand = random.Random()

    async def autotranslate(self, message):
        if message.author == self.bot.user:
            return

        if message.guild.id != 773029270863872050:
            return

        if len(re.findall(u'[\u4e00-\u9fff]+', message.content)) == 0:
            return

        if message.author.id == 969035316008714250:
            if self.rand.random() < self.dog_prob:
                await message.channel.send(f"{message.author}: [I'm a dog woof woof]")
                time.sleep(3)

        await message.channel.send(
            f"{message.author}: {self.deepl.translate_text(message.content, source_lang='ZH', target_lang='EN-GB').text}\n"
            f"{pinyin.get(message.content, delimiter=' ')}")

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.autotranslate(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _: discord.Message, after: discord.Message):
        await self.autotranslate(after)

    @commands.command(name="at_prob")
    async def modify_prob(self, ctx: commands.Context, new_prob: str):
        if ctx.author.id != 264213620026638336:
            return
        self.dog_prob = float(new_prob)


def setup(bot):
    bot.add_cog(Autotranslate(bot))
