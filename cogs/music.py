from _typeshed import Self
from asyncio.base_events import _SendfileFallbackProtocol
import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout
from functools import cmp_to_key, partial
from youtube_dl import YoutubeDL

__all__ = ('NoVoiceClient',"NotSameVoiceChannel","AuthorIsNotInVoiceChannel")

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
    async def create_source(cls, ctx, search: str, *, loop, download=False,playlist=False):
        loop = loop or asyncio.get_event_loop()
        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        if not playlist:
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
    
    async def _playlist_exists(self,guild_id,playlist_name):
        async with self.bot.db.execute("SELECT playlist_id FROM playlists WHERE guild_id = ? AND playlist_name = ?",(guild_id,playlist_name)) as cursor:
            result = await cursor.fetchone()
        return result
    
    @commands.Cog.listener()
    async def on_member_remove(self,member):
        await self.bot.db.execute("UPDATE playlists SET creator_id = ? WHERE creator_id = ?",(None,member.id))
        await self.bot.db.commit()

    async def _count_songs_from_playlist(self,playlist_id):
        async with self.bot.db.execute("SELECT COUNT(*) FROM songs WHERE playlist_id = ?",(playlist_id,)) as cursor:
            result = await cursor.fetchone()
        return result[0] or "0"

    async def _get_playlist_creator_id(self,playlist_id):
        async with self.bot.db.execute("SELECT creator_id FROM playlists WHERE playlist_id = ?",(playlist_id,)) as cursor:
            result = await cursor.fetchone()
        return result

    def register_songs(self,songs):
        songs_list = []
        for song in songs:
            data = ytdl.extract_info(url=song,download=False)
            if 'entries' in data:
                data = data["entries"][0]
            songs_list.append({'webpage_url': data['webpage_url'],'title': data['title']})
        return songs_list

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
                return await ctx.send(f"Already connected to {ctx.voice_client.channel.mention}")#We are already connected to this voice channel.
            else:
                try:
                    await ctx.voice_client.move_to(channel)
                except asyncio.TimeoutError:
                    return await ctx.send(f"Connection to {channel.mention} somehow failed.")
                else:
                    return await ctx.send(f"Now connected to {channel.mention}.",delete_after=10)
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                    return await ctx.send(f"Connection to {channel.mention} somehow failed.")
            else:
                return await ctx.send(f"Now connected to {channel.mention}.",delete_after=10)

    @commands.group(aliases=["sing"])
    async def play(self,ctx,*,song):
        await ctx.message.edit(suppress=True)
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
    
    async def play_playlist(self,ctx,songs_list):
        await ctx.trigger_typing()
        if not ctx.voice_client:
            await ctx.invoke(self.join)
        try:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise NotSameVoiceChannel("You must be in my voice channel to add a song to the queue !")
        except AttributeError: #Author isn't in a voice channel
            raise AuthorIsNotInVoiceChannel("You're not in a voice channel (and to be even more accurate, the voice channel I'm connected to), so you can't use this command.")
        player = self.get_music_player(ctx)
        for song in songs_list:
            source = await YTDLSource.create_source(ctx,song[0],loop=self.bot.loop,download=False,playlist=True)
            await player.queue.put(source)
        return True

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
        player = self.get_music_player(ctx) #Music player for ctx.guild
        if player.queue.empty(): #Nothing to skip if queue is empty
            return await ctx.send("Current queue is empty.")
        voice_client_channel = ctx.voice_client.channel
        voice_channel_members = [member for member in voice_client_channel.members if not member.bot] #Gets every member in the bot's voice channel
        if len(voice_channel_members) == 1 and voice_channel_members[0] == ctx.author: #Command's author is alone in the voice chat, no need to do a vote
            ctx.voice_client.stop()
            return await ctx.send("Song skipped.")
        formatted_choices = "\n".join([f" {self.white_check} Skip, this song is trash.",f"{self.red_cross} This song is dope."])
        em = discord.Embed(title=f"Vote for skipping ! (ends in 10 seconds)",color=0x00ffbb,description=formatted_choices) #Vote for skipping.
        em.set_footer(text="Only people that are in the voice channel in 10 seconds will see their votes counted.")
        poll = await ctx.send(embed=em)
        reactions_list = [self.white_check,self.red_cross]
        for i in reactions_list:
            await poll.add_reaction(i)
        await asyncio.sleep(10) #Wait until the vote ends
        r = discord.utils.get(self.bot.cached_messages,id=poll.id) or await ctx.channel.fetch_message(poll.id) #In case message cannot be found in the bot's cache
        if r is None: #Vote message not in cache neither could be fetched from the channel (most likely was deleteds)
            return await ctx.send("An error occured. Please restart the poll. (the vote message was most likely deleted)")
        reactions_count = []
        for reaction in r.reactions:
            try:
                reactions_count.append((reaction.emoji,len([member for member in await reaction.users().flatten() if not member.bot and member.voice.channel == ctx.voice_client.channel])))
            except AttributeError: #Member.voice is None, so member.voice.channel raises this error. Means someone who voted wasn't in the voice channel at the time.
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

    @commands.command()
    async def playlists(self,ctx):
        playlists_list = []
        em = discord.Embed(title=f"{ctx.guild}'s playlists !",color=discord.Colour.blurple())
        async with self.bot.db.execute("SELECT playlist_id,playlist_name FROM playlists WHERE guild_id = ?",(ctx.guild.id,)) as cursor:
            async for row in cursor:
                playlist_id,playlist_name = row
                number_of_songs = await self._count_songs_from_playlist(playlist_id)
                playlists_list.append(f"`- {playlist_name} ({number_of_songs[0]} songs).`")
        if len(playlists_list) == 0:
            em.description = "Woah. Emptiness."
        else:
            em.description = "\n".join(playlists_list)
        return await ctx.send(embed=em)

    @commands.group(invoke_without_command=True)
    async def playlist(self,ctx,*,playlist_name):
        playlist_exists = await self._playlist_exists(ctx.guild.id,playlist_name)
        if playlist_exists is None:
            return await ctx.send(f"No playlist named '{playlist_name}' was found.")
        playlist_id = playlist_exists[0]
        sql = "SELECT song_url,song_name FROM songs WHERE playlist_id = ? ORDER BY song_position ASC;"
        async with self.bot.db.execute(sql,(playlist_id,)) as cursor:
            playlist_songs = await cursor.fetchall()
        songs_queued = await self.play_playlist(ctx,playlist_songs)
        if songs_queued:
            return await ctx.send(f"Let's go ! I will play the songs of `{playlist_name}` playlist.")

    @playlist.command(aliases=['new'])
    async def create(self,ctx,*args):
        await ctx.message.edit(suppress=True)
        if len(args) == 0:
            return await ctx.send("You didn't give me a playlist name.")
        playlist_exists = await self._playlist_exists(ctx.guild.id,args[0])
        if playlist_exists:
            return await ctx.send(f"A playlist named `{args[0]}` already exists.")
        playlist_created = await self.bot.db.execute_insert("INSERT INTO playlists(playlist_name,creator_id,guild_id,uses) VALUES(?,?,?,0)",(args[0],ctx.author.id,ctx.guild.id))
        await self.bot.db.commit()
        if len(args) > 1:
            nb_songs = len(args) - 1
            await ctx.send(f"Pshhh. Be patient, I need to register {nb_songs} songs.",delete_after=5)
            f = partial(self.register_songs,args[1:])
            songs_list = await self.bot.loop.run_in_executor(None,f)
            sql = "INSERT INTO songs(playlist_id,song_url,song_name,song_position) VALUES(?,?,?,?)"
            counter = 0
            for song in songs_list:
                await self.bot.db.execute(sql,(playlist_created[0],song["webpage_url"],song["title"],counter))
                counter += 1
            await self.bot.db.commit()
            return await ctx.send(f"Successfully created playlist `{args[0]}` ({nb_songs} songs).")
        return await ctx.send(f"Successfully created playlist `{args[0]}`.")

    @playlist.command(aliases=["remove"])
    async def delete(self,ctx,*,playlist_name):
        playlist_exists = await self._playlist_exists(ctx.guild.id,playlist_name)
        if playlist_exists is None:
            return await ctx.send(f"A playlist named `{playlist_name}` doesn't exist.")
        creator_id = await self._get_playlist_creator_id(playlist_exists[0])
        if not(creator_id is None or creator_id[0] == ctx.author.id or ctx.author.guild_permissions.manage_guild):
            return await ctx.send("This playlist has a owner. And you're not the owner. Neither do you have the `manage server` permissions. Thus you can't delete this playlist.")
        try:
            await ctx.send(f"Are you sure you want to delete the `{playlist_name}` playlist ?")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower() == "yes":
                playlist_id = playlist_exists[0]
                await self.bot.db.execute("DELETE FROM songs WHERE playlist_id = ?",(playlist_id,))
                await self.bot.db.execute("DELETE FROM playlists WHERE playlist_id = ?",(playlist_id,))
                await self.bot.db.commit()
                return await ctx.send(f"Done ! Playlist `{playlist_name}` was deleted.")

    @playlist.command()
    async def edit(self,ctx,playlist_name,*,new_playlist_name):
        playlist_exists = await self._playlist_exists(ctx.guild.id,playlist_name)
        if playlist_exists is None:
            return await ctx.send(f"A playlist named `{playlist_name}` doesn't exist.")
        creator_id = await self._get_playlist_creator_id(playlist_exists[0])
        if not(creator_id is None or creator_id[0] == ctx.author.id or ctx.author.guild_permissions.manage_guild):
            return await ctx.send("This playlist has a owner. And you're not the owner. Neither do you have the `manage server` permissions. Thus you can't delete this playlist.")
        await self.bot.db.execute("UPDATE playlists SET playlist_name = ? WHERE playlist_id = ?",(new_playlist_name,playlist_exists[0]))
        await self.bot.db.commit()
        return await ctx.send(f"Playlist name changed : `{playlist_name}` -> `{new_playlist_name}`.")

    @playlist.command()
    async def info(self,ctx,*,playlist_name):
        playlist_exists = await self._playlist_exists(ctx.guild.id,playlist_name)
        if playlist_exists is None:
            return await ctx.send(f"No playlist named '{playlist_name}' was found.")
        playlist_id = playlist_exists[0]
        async with self.bot.db.execute("SELECT creator_id,created_at,uses FROM playlists WHERE playlist_id = ?",(playlist_id,)) as cursor:
            playlist_infos = await cursor.fetchone()
        sql = "SELECT song_url,song_name FROM songs WHERE playlist_id = ? ORDER BY song_position ASC;"
        async with self.bot.db.execute(sql,(playlist_id,)) as cursor:
            playlist_songs = [f"- [`{song[1]}`]({song[0]})" for song in await cursor.fetchall()]
        creator = ctx.guild.get_member(playlist_infos[0]) or "Creator left the server."
        em = discord.Embed(title=f"'{playlist_name}' playlist - {len(playlist_songs)} songs.",description="\n".join(playlist_songs))
        em.add_field(name="Created at :",value=playlist_infos[1])
        em.add_field(name="Creator :",value=creator.mention)
        em.add_field(name="Uses : ",value=playlist_infos[2])
        return await ctx.send(embed=em)
        
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