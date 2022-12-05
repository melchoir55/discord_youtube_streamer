import os

import discord
from discord import Option
from discord.ext import commands
from dotenv import load_dotenv
from Music import Music
from Listener import ListenerCog
import pymongo
import datetime

from YTDL import YTDLSource

load_dotenv()
# Get the API token from the .env file.
BOT_OWNER_USER_NAME = os.getenv("BOT_OWNER_USER_NAME")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

initial_extensions = ['cogs.listener',
                      'cogs.music']

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

mongo_client = pymongo.MongoClient(MONGO_URI)
bot.mongo_db = mongo_client.youtube_streamer


@bot.slash_command(name='play', description="streams music")
async def play_(ctx: discord.ApplicationContext,
                *,
                search: Option(str,
                                description="The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.",
                                required=True)):
    """Request a song and add it to the queue.
    This command attempts to join a valid voice channel if the bot is not already in one.
    Uses YTDL to automatically search and retrieve a song.

    Args:
    search (str): The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
    """
    await ctx.trigger_typing()

    vc = ctx.voice_client

    if not vc:
        await ctx.invoke(self.connect_)

    player = await self.get_player(ctx)

    # If download is False, source will be a dict which will be used later to regather the stream.
    # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
    source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)

    await player.queue.put(source)

@bot.event
async def on_guild_join(guild):
    guilds = bot.mongo_db.guilds
    this_guild = guilds.find_one({"guild_id": guild.id})
    if this_guild:
        return

    inserted = guilds.insert_one({
        "guild_id": guild.id,
        "name": guild.name,
        "volume": 5,
        "authorized": False,
        "added_by": {
            "name": str(guild.owner),
            "id": guild.owner.id
        },
        "created_at": datetime.datetime.utcnow()
    })

    guild_owner = await bot.fetch_user(guild.owner.id)
    await guild_owner.send(f"You recently added me to {guild.name}. I cannot be used until authorized by whoever is running the bot. Please contact the bot admin to request authorization for your server.")

    owner_name = os.getenv("BOT_OWNER_USER_NAME").split('#')[0]
    discriminator = os.getenv("BOT_OWNER_USER_NAME").split('#')[1]
    bot_owner = discord.utils.get(bot.get_all_members(), name=owner_name, discriminator=discriminator)
    await bot_owner.send(f"A new Guild is attempting to use the bot {guild.name} ({guild.id})\n"
                   f"Guild owner contact: {str(guild.owner)} ({guild.owner.id})")

if __name__ == "__main__":
    bot.add_cog(ListenerCog(bot))
    bot.run(DISCORD_TOKEN)
