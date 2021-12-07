import asyncio
import collections

import discord
from discord.ext import commands

from Track import Track
from YTDL import YTDLSource

song_queue = collections.deque()
history = collections.deque()
currentVoiceClient = None
currentVoiceChannel = None
currentSongData = None
guildTextChannel = None
currentTrack = None
is_playing = False
runningTask = None


def get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def add_songs_to_song_queue(data):
    for song in data:
        song_queue.appendleft(Track(song['artist'] + ' - ' + song['title'], song['webpage_url']))


class MusicPlayerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # region bot.commands

    @commands.command(name='play', help='To play song')
    async def play(self, ctx, url=None):
        global history
        global currentVoiceClient
        global currentVoiceChannel
        global guildTextChannel
        global currentTrack
        global is_playing

        if currentTrack:
            history.append(currentTrack)
            currentTrack = None
        if url is None:
            if song_queue:
                track = song_queue.pop()
                currentTrack = track
                url = track.url
            else:
                await ctx.send('Nothing to play')
                return
        try:
            await self.join(ctx)
            if ctx is not None and ctx.message.guild.voice_client is not None and ctx.message.guild.voice_channels[
                0] is not None:
                currentVoiceClient = ctx.message.guild.voice_client
                currentVoiceChannel = ctx.message.guild.voice_channels[0]
                for text_channel in ctx.message.guild.text_channels:
                    if str(text_channel) == "bot-control":
                        guildTextChannel = text_channel

            await self.download_song_data(url)

        except RuntimeError as err:
            print(f"Unexpected {err=}, {type(err)=}")

    @commands.command(name='add', help='Adds a track to the queue')
    async def add_song(self, ctx, url):
        global currentTrack
        try:
            async with ctx.typing():
                file_data = await YTDLSource.from_url(url, loops=self.bot.loop)
                # If there is a playlist:
                if type(file_data) is list:
                    add_songs_to_song_queue(file_data)
                # If single track:
                else:
                    song_queue.appendleft(
                        Track(file_data['artist'] + ' - ' + file_data['title'], file_data['webpage_url']))
                await self.print_queue(ctx)
        except:
            await ctx.send("Some error occurred while accessing ytdl")

    @commands.command(name='queue', help='Prints queue and previous songs')
    async def print_queue(self, ctx):
        s = ""
        s += "-------------Previous-------------\n"
        if len(history) > 0:
            for track in history:
                s += track.filename + "\n"
        if currentTrack:
            s += "--------------Playing-------------\n"
            s += "**" + currentTrack.filename + "** \n"
        s += "-------------In Queue-------------\n"
        # Reversed for songs to upper in order: next song on toppy
        for track in reversed(song_queue):
            s += track.filename + "\n"

        await ctx.send(s)

    @commands.command(name='next', help='')
    async def next_song(self, ctx):
        await self.play(ctx)

    @commands.command(name='prev', help='')
    async def prev(self, ctx):
        global song_queue
        track = history.pop()
        song_queue.append(currentTrack)
        await self.download_song_data(track.url)

    @commands.command(name='join', help='Tells the bot to join the voice channel')
    async def join(self, ctx):
        if ctx is None:
            return
        if not ctx.message.author.voice:
            await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        if ctx.message.guild.voice_client:
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()

    @commands.command(name='pause', help='This command pauses the song')
    async def pause(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name='resume', help='Resumes the song')
    async def resume(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
        else:
            await ctx.send("The bot was not playing anything before this. Use play_song command")

    @commands.command(name='leave', help='To make the bot leave the voice channel')
    async def leave(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            song_queue.clear()
            history.clear()
            await voice_client.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    @commands.command(name='stop', help='Stops the song')
    async def stop(self, ctx):
        voice_client = ctx.message.guild.voice_client
        global is_playing
        global currentTrack
        if voice_client.is_playing():
            voice_client.stop()
            is_playing = False
            history.append(currentTrack)
            currentTrack = None
            runningTask.cancel()
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    # endregion

    async def download_song_data(self, url):
        data = await YTDLSource.from_url(url, loops=self.bot.loop)
        if type(data) is list:  # If playlist
            add_songs_to_song_queue(data[1:])
            await self.play_song(data[0])
        else:
            await self.play_song(data)
        return data

    async def play_song(self, song):
        global currentTrack, is_playing, currentVoiceClient, runningTask
        file_name = song['artist'] + ' - ' + song['title']
        duration = song['duration']
        currentTrack = Track(file_name, song['webpage_url'])
        audio_stream = discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=song['url'], options='-vn',
                                              before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
        print('Song Duration: ', duration)
        is_playing = True
        await guildTextChannel.send('Playing **' + file_name + '**')
        currentVoiceClient.stop()
        currentVoiceClient.play(audio_stream, after=lambda e: print('Player error: %s' % e) if e else None)
        if runningTask:
            runningTask.cancel()
            runningTask = None
        runningTask = asyncio.create_task(self.play_next_on_end(duration))
        await runningTask

    async def play_next_on_end(self, duration):
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
            loop.create_task(self.download_song_data(track.url))
