import asyncio
import collections
import discord
from discord.ext import commands,tasks
import os
from dotenv import load_dotenv
import youtube_dl


load_dotenv()
# Get the API token from the .env file.
DISCORD_TOKEN = os.getenv("discord_token")

print(DISCORD_TOKEN)

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)


youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
playlist = collections.deque()
playhist = collections.deque()


class Track:
    def __init__(self, filename, url):
        self.filename = filename
        self.url = url

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]     
        filename = data['url'] if stream else ytdl.prepare_filename(data)       
        return filename

playingtrack = False

@bot.command(name='play', help='To play song')
async def play(ctx,url = None):
    global playhist
    if url == None:
        if playlist:
            track = playlist.pop()
            playhist.append(track)
            url = track.url
        else:
            await ctx.send('Nothing to play')
            return
    try :
        global playingtrack
        await join(ctx)
        voice_client = ctx.message.guild.voice_client
        if playingtrack:
            voice_client.stop()       
        async with ctx.typing():
            filename = await YTDLSource.from_url(url, loop=bot.loop)           
            playlist.appendleft(Track(filename, url))
            song = discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename)
            voice_client.play(song)
            playingtrack = True        
        await ctx.send('**Playing**')
                
    except:        
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command(name = 'add', help='Adds a track to the queue')
async def add(ctx, url):
    try:
         async with ctx.typing():
            filename = await YTDLSource.from_url(url, loop=bot.loop)
            playlist.appendleft(Track(filename, url))
         await ctx.send("Added song to queue. Count: " + len(playlist).__str__())
         for track in playlist:
            await ctx.send(track.url)         
    except:
        await ctx.send("Some error occurred while accessing ytdl")

@bot.command(name = 'next', help = '')
async def next(ctx):
    await play(ctx)

@bot.command(name='prev', help = '')
async def prev(ctx):
    global playlist
    track = playhist.pop()
    playlist.appendleft(track)
    await play(ctx)

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    if ctx.message.guild.voice_client:
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()


@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")
    
@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")
    


@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    global playingtrack
    if voice_client.is_playing():
        voice_client.stop()
        playingtrack = False     
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.event
async def on_ready():
    print('Running!')
    for guild in bot.guilds:
        for channel in guild.text_channels :
            if str(channel) == "general" :
                await channel.send('Bot Activated..')
        print('Active in {}\n Member Count : {}'.format(guild.name,guild.member_count))

@bot.command(help = "Prints details of Author")
async def whats_my_name(ctx) :
    await ctx.send('Hello {}'.format(ctx.author.name))

@bot.command(help = "Prints details of Server")
async def where_am_i(ctx):
    owner=str(ctx.guild.owner)
    region = str(ctx.guild.region)
    guild_id = str(ctx.guild.id)
    memberCount = str(ctx.guild.member_count)
    icon = str(ctx.guild.icon_url)
    desc=ctx.guild.description
    
    embed = discord.Embed(
        title=ctx.guild.name + " Server Information",
        description=desc,
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=icon)
    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="Server ID", value=guild_id, inline=True)
    embed.add_field(name="Region", value=region, inline=True)
    embed.add_field(name="Member Count", value=memberCount, inline=True)

    await ctx.send(embed=embed)

    members=[]
    async for member in ctx.guild.fetch_members(limit=150) :
        await ctx.send('Name : {}\t Status : {}\n Joined at {}'.format(member.display_name,str(member.status),str(member.joined_at)))

    


@bot.event
async def on_member_join(member):
     for channel in member.guild.text_channels :
         if str(channel) == "general" :
             on_mobile=False
             if member.is_on_mobile() == True :
                 on_mobile = True
             await channel.send("Welcome to the Server {}!!\n On Mobile : {}".format(member.name,on_mobile))             
 
@bot.event
async def on_message(message) :
    # bot.process_commands(msg) is a couroutine that must be called here since we are overriding the on_message event
    await bot.process_commands(message) 
    if str(message.content).lower() == "hello":
        await message.channel.send('Hi!')
    
    if str(message.content).lower() in ['swear_word1','swear_word2']:
        await message.channel.purge(limit=1)


if __name__ == "__main__" :
    bot.run(DISCORD_TOKEN)