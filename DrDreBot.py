import asyncio
import collections
from logging import error
from time import sleep
import discord
from discord.ext import commands,tasks
import os
from discord.ext.commands.bot import Bot
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
currentVoiceClient = None
currentVoiceChannel = None
currentSongData = None
guildTextChannel = None
currentTrack = None

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
    async def from_url(cls, url, *, loops=None, stream=True):
        loop = None
        if loops is None:
            loop = asyncio.get_event_loop()  
        else:
            loop = loops            
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]    

        fileName = data['artist'] + ' - ' + data['title'] 
        if not fileName:
            fileName = ytdl.prepare_filename(data)
        url = data['url']    
        time = data['duration']
        #return url, fileName, time
        return data

def get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()        
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

playingtrack = False

@bot.command(name='play', help='To play song')
async def play(ctx,url = None):
    global playhist
    global currentVoiceClient
    global currentVoiceChannel
    global guildTextChannel
    global currentTrack
    
    if url == None:
        if playlist:
            playhist.append(currentTrack)
            track = playlist.pop()
            currentTrack = track
            url = track.url
        else:
            await ctx.send('Nothing to play')
            return
    try :
        global playingtrack
        await join(ctx)
        if ctx is not None and ctx.message.guild.voice_client is not None and ctx.message.guild.voice_channels[0] is not None:
            currentVoiceClient = ctx.message.guild.voice_client
            currentVoiceChannel = ctx.message.guild.voice_channels[0]
            guildTextChannel = ctx.message.guild.text_channels[0] 
        
        await download_song(url)

                
    except:        
        await ctx.send("The bot is not connected to a voice channel.")

async def download_song(url):
    global currentTrack
    fileData = await YTDLSource.from_url(url, loops=bot.loop)  
    fileName = fileData['artist'] + ' - ' + fileData['title']
    duration = fileData['duration']
    currentTrack = Track(fileName, url)
    song = discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=fileData['url'], before_options="-re")            
    playingtrack = True 
    await guildTextChannel.send('Playing **' + fileName + '**')
    await start_playing(song, duration)
    return fileData

async def start_playing(song, duration):
    currentVoiceClient.stop()      
    currentVoiceClient.play(song)
    await asyncio.sleep(duration)
    playNext(None)

@bot.command(name = 'add', help='Adds a track to the queue')
async def add(ctx, url):
    try:
         async with ctx.typing():
            fileData = await YTDLSource.from_url(url, loops=bot.loop)
            playlist.appendleft(Track(fileData['artist'] + ' - ' + fileData['title'], url))
            await queue(ctx)
    except:
        await ctx.send("Some error occurred while accessing ytdl")

@bot.command(name='queue', help = 'Prints queue and previous songs')
async def queue(ctx):
        s = ""
        s += "Playing : **" + currentTrack.filename + "** \n"
        s += "-------------In Queue-------------\n"
        #Reversed for songs to upper in order: next song on toppy    
        for track in reversed(playlist):
            s += track.filename + "\n"   
        s += "-------------Previous-------------\n"
        for track in playhist:
            s += track.filename + "\n"  
        await ctx.send(s)

@bot.command(name = 'next', help = '')
async def next(ctx):
    await play(ctx)


def playNext(error):
    global playhist
    global playlist
    global currentVoiceClient
    global currentVoiceChannel
    if playlist:
            playhist.append(currentTrack)
            track = playlist.pop()
            loop = asyncio.get_event_loop()
            loop.create_task(download_song(track.url))

@bot.command(name='prev', help = '')
async def prev(ctx):
    global playlist
    track = playhist.pop()
    playlist.appendleft(track)
    await download_song(track.url)

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if ctx == None:
        return
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
        playlist.clear()
        playhist.clear()
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

@bot.event
async def on_voice_state_update(member, before, after):
    if member.name == "DrDreBot":
        if before.channel is None and after.channel is not None:
            await member.guild.text_channels[0].send("Lets Jam!")        
 
@bot.event
async def on_message(message) :
    # bot.process_commands(msg) is a couroutine that must be called here since we are overriding the on_message event
    await bot.process_commands(message)


if __name__ == "__main__" :
    bot.run(DISCORD_TOKEN)