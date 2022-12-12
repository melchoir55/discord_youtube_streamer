# Warning

This bot exists for educational purposes only. 
The author does not accept liability for any damages suffered from its use. 
Ensure that you are not violating the TOS of any service you interact with using this bot.

# Run

Install docker. Then run:

`DISCORD_TOKEN=<your discord bot token> BOT_OWNER_USER_NAME=<the discord user to send admin messages to> docker-compose up`

## All valid env vars
* DISCORD_TOKEN: Token obtained from discord. Setup an app here: https://discordapp.com/developers/applications/
* MONGO_URI: The uri to the mongo database. Defaults to `mongodb://localhost:27017`
* BOT_OWNER_USER_NAME: The discord user to send admin messages to. Must be in one of the servers in which the bot is a member.

# Authorize Guilds

Whenever a new server tries to run the bot, it must be explicitly authorized. Connect to the mongo db instance using
mongo compass, retrieve the doc for the server in youtube_streamer.guilds, and set `authorized` to `True`.