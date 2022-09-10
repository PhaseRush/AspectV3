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

        msg: str = message.content
        chinese_blocks = {}

        already_trolled: bool = False
        for block in re.findall(r'[\u4e00-\u9fff]+', msg):
            chinese_blocks[block] = self.deepl.translate_text(block, source_lang="ZH", target_lang="EN-GB").text
            if message.author.id == 969035316008714250:
                if self.rand.random() < 0.1 and not already_trolled:
                    await message.channel.send("[I'm a dog woof woof]")
                    time.sleep(3)
                    already_trolled = True

        if len(chinese_blocks) == 0:
            return

        build_msg: str = msg
        for zh, en in chinese_blocks.items():
            build_msg = build_msg.replace(zh, f"[{en}]")

        await message.channel.send(build_msg)


def setup(bot):
    bot.add_cog(Autotranslate(bot))
