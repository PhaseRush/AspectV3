from discord.ext import commands


class VoiceCog(commands.Cog, name="Voice"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['stfu'])
    async def muteall(self, ctx: commands.Context):
        [await member.edit(mute=True) for member in ctx.author.voice.channel.members]

    @commands.command()
    async def unmuteall(self, ctx: commands.Context):
        [await member.edit(mute=False) for member in ctx.author.voice.channel.members]


def setup(bot):
    bot.add_cog(VoiceCog(bot))
