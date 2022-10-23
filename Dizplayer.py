import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from Music import Music

load_dotenv()
# Get the API token from the .env file.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
print(DISCORD_TOKEN)

initial_extensions = ['cogs.listener',
                      'cogs.music']

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

if __name__ == "__main__":
    bot.add_cog(Music(bot))
    bot.run(DISCORD_TOKEN)
