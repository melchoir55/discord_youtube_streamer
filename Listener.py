from discord.ext import commands


class ListenerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # region bot.events
    @commands.Cog.listener()
    async def on_ready(self):
        print('Running!')
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if str(channel) == "bot-control":
                    await channel.send('Bot Activated..')
            print('Active in {}\n Member Count : {}'.format(guild.name, guild.member_count))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.name == "Dizplayer":
            if before.channel is None and after.channel is not None:
                for channel in member.guild.text_channels:
                    if str(channel) == "bot-control":
                        await channel.send("Lets Jam!")

    # endregion
