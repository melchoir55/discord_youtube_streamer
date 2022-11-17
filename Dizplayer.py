import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from Music import Music
from Listener import ListenerCog
import pymongo

load_dotenv()
# Get the API token from the .env file.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
print(DISCORD_TOKEN)

initial_extensions = ['cogs.listener',
                      'cogs.music']

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

mongo_client = pymongo.MongoClient(MONGO_URI)
bot.mongo_db = mongo_client.youtube_streamer

if __name__ == "__main__":
    bot.add_cog(Music(bot))
    bot.add_cog(ListenerCog(bot))
    bot.run(DISCORD_TOKEN)
