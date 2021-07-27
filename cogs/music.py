import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout
from functools import partial
from youtube_dl import YoutubeDL


ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

class NoVoiceClient(commands.CommandError):
    """A class to represents the lack of a VoiceClient for a guild"""

class NotSameVoiceChannel(commands.CommandError):
    """A class to represents the fact that command's author isn't in the same voice channel as the bot."""    

class AuthorIsNotInVoiceChannel(commands.CommandError):
    """A class that represents the fact that command's author isn't in a voice channel."""


ytdl = YoutubeDL(ytdlopts)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()
        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        await ctx.send(f'Added `{data["title"]}` to the queue.', delete_after=15)
        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}
        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)
        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

class MusicPlayer:

    def __init__(self,ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog
        self.queue = asyncio.Queue()
        self.run_next = asyncio.Event()
        self.now_playing = None
        self.volume = .5
        self.current = None
        ctx.bot.loop.create_task(self.music_player_loop())
    
    async def music_player_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            self.run_next.clear()
            try:
                async with timeout(600):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                await self._destroy(self._guild)
            source = await YTDLSource.regather_stream(source,loop=self.bot.loop)
            source.volume = self.volume
            self.current = source
            self._guild.voice_client.play(source,after=lambda _:self.bot.loop.call_soon_threadsafe(self.run_next.set)) #Sets the event when the song is done, means it is now not blocking.
            self.now_playing = await self._channel.send(f"Now playing : `{source['title']}`.")
            await self.run_next.wait()
            try:
                await self.now_playing.delete()
            except discord.Forbidden:
                pass
        
    async def _destroy(self,guild):
        return self.bot.loop.create_task(self._cog.cleanup(guild))

class Music(commands.Cog):
    
    def __init__(self,bot) -> None:
        self.bot = bot
        self.players = {}
        self.white_check = "\U00002705"
        self.red_cross = "\U0000274c"
    
    async def cleanup(self,guild):
        try:
            await guild.voice_client.disconnect()
        except Exception as e:
            print(e)
        try:
            del self.players[guild.id]
        except Exception as e:
            print(e)

    def get_music_player(self,ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.command(aliases=["connect"])
    async def join(self,ctx,*,channel : discord.VoiceChannel=None):
        if channel is None:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise AuthorIsNotInVoiceChannel("Either join a voice channel or specify one !")
        if ctx.voice_client:
            if ctx.voice_client.channel.id == channel.id:
                return #We are already connected to this voice channel.
            else:
                try:
                    await ctx.voice_client.move_to(channel)
                except asyncio.TimeoutError:
                    return await ctx.send(f"Connection to {channel.mention} somehow failed.")
                else:
                    return await ctx.send(f"Now connected to {channel.mention}.",delete_after=15)
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                    return await ctx.send(f"Connection to {channel.mention} somehow failed.")
            else:
                return await ctx.send(f"Now connected to {channel.mention}.",delete_after=15)

    @commands.command(aliases=["sing"])
    async def play(self,ctx,*,song):
        await ctx.trigger_typing()
        if not ctx.voice_client:
            await ctx.invoke(self.join)
        try:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise NotSameVoiceChannel("You must be in my voice channel to add a song to the queue !")
        except AttributeError: #Author isn't in a voice channel
            raise AuthorIsNotInVoiceChannel("You're not in a voice channel (and to be even more accurate, the voice channel I'm connected to), so you can't use this command.")
        player = self.get_music_player(ctx)
        source = await YTDLSource.create_source(ctx,song,loop=self.bot.loop,download=False)
        await player.queue.put(source)
    
    @commands.command()
    async def stop(self,ctx):
        await self.cleanup(ctx.guild)
        return await ctx.send("Disconnected.")

    @commands.command()
    async def pause(self,ctx):
        if ctx.voice_client.is_paused():
            return await ctx.send("The song is already paused.")
        ctx.voice_client.pause()
        return await ctx.send(f"Song paused. (requested by {ctx.author.mention})",allowed_mentions=self.bot.no_mentions)

    @commands.command()
    async def skip(self,ctx):
        if not ctx.voice_client.is_playing(): #Self explanatory
            return await ctx.send("I'm not playing anything.")
        voice_client_channel = ctx.voice_client.channel
        voice_channel_members = [member for member in voice_client_channel.members if not member.bot] #Gets every member in the bot's voice channel
        if len(voice_channel_members) == 1 and voice_channel_members[0] == ctx.author: #Command's author is alone in the voice chat, no need to do a vote
            ctx.voice_client.stop()
            return await ctx.send("Song skipped.")
        formatted_choices = "\n".join([f" {self.white_check} Skip, this song is trash.",f"{self.red_cross} This song is dope."])
        em = discord.Embed(title=f"Vote for skipping ! (ends in 10 seconds)",color=0x00ffbb,description=formatted_choices)
        poll = await ctx.send(embed=em)
        reactions_list = [self.white_check,self.red_cross]
        for i in reactions_list:
            await poll.add_reaction(i)
        await asyncio.sleep(10)
        r = discord.utils.get(self.bot.cached_messages,id=poll.id) or await ctx.channel.fetch_message(poll.id)
        if r is None:
            return await ctx.send("An error occured. Please restart the poll.")
        reactions_count = []
        for reaction in r.reactions:
            try:
                reactions_count.append((reaction.emoji,len([member for member in await reaction.users().flatten() if not member.bot and member.voice.channel == ctx.voice_client.channel])))
            except AttributeError: #Member.voice is None, so member.voice.channel raises this error
                continue
        maxi = max(reactions_count,key=lambda item:item[1])
        if maxi[1] == 0:
            return await ctx.send("Well, no one voted. What do I do now..")
        elif maxi[0] == "✅":
            await ctx.send(f"Skipping song ({maxi[1]} votes).")
            ctx.voice_client.stop()
        else:
            return await ctx.send(f"I hate democracy ({maxi[1]} votes).")

    @commands.command()
    async def resume(self,ctx):
        if ctx.voice_client.is_playing():
            return await ctx.send("I'm already playing something !")
        ctx.voice_client.resume()
        return await ctx.send(f"Song resumed. (requested by {ctx.author.mention})",allowed_mentions=self.bot.no_mentions)

    @commands.command()
    async def queue(self,ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            raise NoVoiceClient("Not connected to a voice channel.")
        if player.queue.empty():
            return await ctx.send("Current queue is empty.")
        queue = player.queue._queue
        queue_size = player.queue.qsize()
        max_song = min(10,queue_size)
        formatted_queue = "\n".join([f"- [`{queue[i]['title']}`]({queue[i]['webpage_url']})  ({queue[i]['requester'].mention})" for i in range(max_song)])
        em = discord.Embed(title="Upcoming songs - ",color=discord.Colour.blurple(),description=formatted_queue)
        if queue_size > 10:
            em.set_footer(text=f"{queue_size - 10} others songs upcoming !")
        return await ctx.send(embed=em)

    @commands.command()
    async def volume(self,ctx,vol:int):
        if not ctx.voice_client.is_playing():
            return await ctx.send("I'm not playing anything.")
        if not (0 < vol < 101):
            return await ctx.send("Please, pick a number between 1 and 100.")
        player = self.get_music_player(ctx)
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = vol/100
        player.volume = vol/100
        return await ctx.send(f"Volume set to {vol}.")

    @pause.before_invoke
    @stop.before_invoke
    @resume.before_invoke
    @skip.before_invoke
    @queue.before_invoke
    @volume.before_invoke
    async def ensure_same_voice_channel(self,ctx):
        if ctx.voice_client is None:
            raise NoVoiceClient("I'm currently not connected to a voice channel.")        
        try:
            authors_vc = ctx.author.voice.channel
        except AttributeError: #Author isn't in a voice channel
            raise AuthorIsNotInVoiceChannel("You must be connected to a voice channel (actually, my voice channel) to use this command.")
        else:
            if authors_vc != ctx.voice_client.channel: #Author isn't in the same voice channel as bot
                raise NotSameVoiceChannel("You must be connected to my voice channel to use this command.")


def setup(bot):
    bot.add_cog(Music(bot))