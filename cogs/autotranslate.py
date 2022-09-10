import random
import time

from discord.ext import commands
import re
import deepl
from config import DEEPL_TOKEN


class Autotranslate(commands.Cog, name="Autotranslate"):
    def __init__(self, bot):
        self.bot = bot
        self.deepl = deepl.Translator(DEEPL_TOKEN)
        self.rand = random.Random()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.guild.id != 773029270863872050:
            return

        if len(re.findall(u'[\u4e00-\u9fff]+', message.content)) == 0:
            return

        if message.author.id == 969035316008714250:
            if self.rand.random() < 0.1:
                await message.channel.send("[I'm a dog woof woof]")
                time.sleep(3)

        await message.channel.send(f"{message.author}: {self.deepl.translate_text(message.content, source_lang='ZH', target_lang='EN-GB').text}")


def setup(bot):
    bot.add_cog(Autotranslate(bot))
