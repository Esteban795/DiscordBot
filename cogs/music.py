import asyncio
import discord
import youtube_dl
from discord.ext import commands

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
class YTDLSource(discord.PCMVolumeTransformer): #subclass of discord.PCMVolumeTransformer
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a url (doesn't predownload)"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player)
        await ctx.send(f'Now playing: {player.title}')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()
    
    @commands.command()
    async def pause(self,ctx):
        """Pauses the guild's voice client"""
        ctx.voice_client.pause()
    
    @commands.command()
    async def resume(self,ctx):
        """Resume's the guild's voice_client"""
        ctx.voice_client.resume()

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("You are not connected to a voice channel.")
        else:
            if ctx.author.voice and ctx.author.voice.channel == ctx.voice_client.channel:
                ctx.voice_client.stop()
            else:
                return await ctx.send("You must be connected to the bot's voice channel.")

    @pause.before_invoke
    @resume.before_invoke
    @stop.before_invoke
    async def ensure_same_voice_channel(self,ctx):
        if ctx.voice_client:
            if not ctx.author.voice or ctx.author.voice.channel != ctx.voice_client.channel:
                return await ctx.send("You must be connected to the bot's voice channel.")
            else:
                return True
        else:
            return await ctx.send("I'm not even connected to a voice channel.")

def setup(bot):
    bot.add_cog(Music(bot))