import asyncio
import collections
import os

import discord
import nest_asyncio
import youtube_dl
from discord.ext import commands
from dotenv import load_dotenv

from Track import Track
from YTDL import YTDLSource

nest_asyncio.apply()
load_dotenv()
# Get the API token from the .env file.
DISCORD_TOKEN = os.getenv("discord_token")

print(DISCORD_TOKEN)

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)

song_queue = collections.deque()
history = collections.deque()
currentVoiceClient = None
currentVoiceChannel = None
currentSongData = None
guildTextChannel = None
currentTrack = None
playingtrack = False
runningTask = None

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

# region bot.commands


@bot.command(name='play', help='To play song')
async def play(ctx, url=None):
    global history
    global currentVoiceClient
    global currentVoiceChannel
    global guildTextChannel
    global currentTrack
    global playingtrack

    if currentTrack:
        history.append(currentTrack)
    if url == None:
        if song_queue:
            track = song_queue.pop()
            currentTrack = track
            url = track.url
        else:
            await ctx.send('Nothing to play')
            return
    try:
        await join(ctx)
        if ctx is not None and ctx.message.guild.voice_client is not None and ctx.message.guild.voice_channels[
            0] is not None:
            currentVoiceClient = ctx.message.guild.voice_client
            currentVoiceChannel = ctx.message.guild.voice_channels[0]
            for text_channel in ctx.message.guild.text_channels:
                if str(text_channel) == "bot-control":
                    guildTextChannel = text_channel

        await download_song_data(url)

    except RuntimeError as err:
        print(f"Unexpected {err=}, {type(err)=}")


@bot.command(name='add', help='Adds a track to the queue')
async def add_song(ctx, url):
    global currentTrack
    try:
        async with ctx.typing():
            fileData = await YTDLSource.from_url(url, loops=bot.loop)

            if type(fileData) is list:
                if currentTrack is None:
                    currentTrack = fileData[0]
                    for song in fileData[1:]:
                        song_queue.appendleft(Track(song['artist'] + ' - ' + song['title'], song['webpage_url']))
                else:
                    for song in fileData:
                        song_queue.appendleft(Track(song['artist'] + ' - ' + song['title'], song['webpage_url']))
            else:
                song_queue.appendleft(Track(fileData['artist'] + ' - ' + fileData['title'], fileData['webpage_url']))

            await queue(ctx)
    except:
        await ctx.send("Some error occurred while accessing ytdl")


@bot.command(name='queue', help='Prints queue and previous songs')
async def queue(ctx):
    s = ""
    if currentTrack:
        s += "Playing : **" + currentTrack.filename + "** \n"
    s += "-------------In Queue-------------\n"
    # Reversed for songs to upper in order: next song on toppy
    for track in reversed(song_queue):
        s += track.filename + "\n"
    s += "-------------Previous-------------\n"
    if len(history) > 0:
        for track in history:
            s += track.filename + "\n"
    await ctx.send(s)


@bot.command(name='next', help='')
async def next_song(ctx):
    await play(ctx)


@bot.command(name='prev', help='')
async def prev(ctx):
    global song_queue
    track = history.pop()
    song_queue.appendleft(track)
    await download_song_data(track.url)


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
        song_queue.clear()
        history.clear()
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


# endregion

# region bot.events
@bot.event
async def on_ready():
    print('Running!')
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if str(channel) == "bot-control":
                await channel.send('Bot Activated..')
        print('Active in {}\n Member Count : {}'.format(guild.name, guild.member_count))


@bot.event
async def on_voice_state_update(member, before, after):
    if member.name == "DrDreBot":
        if before.channel is None and after.channel is not None:
            for channel in member.guild.text_channels:
                if str(channel) == "bot-control":
                    await channel.send("Lets Jam!")


@bot.event
async def on_message(message):
    # bot.process_commands(msg) is a couroutine that must be called here since we are overriding the on_message event
    await bot.process_commands(message)


# endregion


def get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


async def download_song_data(url):
    global currentTrack
    global playingtrack
    data = await YTDLSource.from_url(url, loops=get_or_create_event_loop())
    if type(data) is list:  # If playlist
        await add_songs_to_song_queue(data)
        await play_song(data[0])
    else:
        await play_song(data)
    return data


async def play_song(song):
    global currentTrack, playingtrack, runningTask, currentVoiceClient
    file_name = song['artist'] + ' - ' + song['title']
    duration = song['duration']
    currentTrack = Track(file_name, song['webpage_url'])
    audio_stream = discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=song['url'], options='-vn',
                                          before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
    if playingtrack:
        currentVoiceClient.stop()
    print('Song Duration: ', duration)
    playingtrack = True
    await guildTextChannel.send('Playing **' + file_name + '**')
    currentVoiceClient.play(audio_stream, after=lambda e: print('Player error: %s' % e) if e else None)
    if runningTask:
        runningTask.cancel()
        runningTask = None
    runningTask = asyncio.create_task(play_next_on_end(duration))
    await runningTask


async def play_next_on_end(duration):
    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        print('cancel sleep')
        return
    print('End sleep, playing next')
    if song_queue:
        history.append(currentTrack)
        track = song_queue.pop()
        loop = get_or_create_event_loop()
        loop.create_task(download_song_data(track.url))


async def add_songs_to_song_queue(data):
    for song in data[1:]:
        song_queue.appendleft(Track(song['artist'] + ' - ' + song['title'], song['webpage_url']))
        # await queue(ctx)
