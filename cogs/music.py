import itertools
import discord
from discord.ext import commands,menus
import asyncio
from async_timeout import timeout
from functools import partial
from dotenv import load_dotenv
from youtube_dl import YoutubeDL
from fuzzywuzzy import process
import re
import random
import asyncspotify
import os
import datetime

load_dotenv()
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


__all__ = ('NoVoiceClient',"NotSameVoiceChannel","AuthorIsNotInVoiceChannel","PlaylistNotFound","SongNotInPlaylist","InvalidSlice","InvalidPlaylistLink")

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

class PlaylistNotFound(commands.CommandError):
    """A class that represents the fact that a playlist named [something] doesn't exist, neither have close match."""

class SongNotFound(commands.CommandError):
    """A class that represents the fact that a song doesn't exist in the playlist."""

class SongNotInPlaylist(commands.CommandError):
    """A class that represents the fact that a song doesn't exist in the playlist yet."""

class InvalidSlice(commands.CommandError):
    """A class that represents that the fact that was inputted is wrong (doesn't match \d:\d)"""

class InvalidPlaylistLink(commands.CommandError):
    """A class that represents the fact a playlist share link wasn't the right one. Should look like : https://open.spotify.com/playlist/2Uor0e3UQxqCNRKmYpchpV?si=be08ba908c1744fb"""

class LowerConverter(commands.Converter):
    """Converts the argument to lower case."""
    async def convert(self, ctx, argument):
        return argument.lower()

class SliceConverter(commands.Converter):
    """Converts the slice argument into a start,end numbers."""
    async def convert(self, ctx, argument):
        slice_regex = re.compile(r"(\d{1,5}):(\d{1,5})")
        result = slice_regex.findall(argument)
        if not result:
            raise InvalidSlice(f"`{argument}`` is not a valid slice. A slice must be of the form a:b, with a <= b. (a and b are numbers)")
        start,end = [int(i) for i in result[0]]
        if end < start:
            raise InvalidSlice(f"`{argument}` is not a valid slice, because the end is lower than the start.")
        return (start,end)

class PlaylistsDisplayer(menus.ListPageSource):
    async def format_page(self, menu, item):
        embed = discord.Embed(title="Playlists available : ",description="\n".join(item))
        return embed

class PlaylistInfosDisplayer(menus.ListPageSource):

    def __init__(self, entries, *, per_page,tp,author,title):
        super().__init__(entries, per_page=per_page)
        self.timestamp = tp
        self.creator = author
        self.playlist_title = title

    async def format_page(self, menu, item):
        embed = discord.Embed(title=f"`{self.playlist_title}` playlist.",description="\n".join(item))
        embed.add_field(name="Created at :",value=f"<t:{self.timestamp}:f>")
        embed.add_field(name="Creator :",value=self.creator.mention)
        return embed

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

class CustomQueue(asyncio.Queue):

    def __getitem__(self,item):
        if isinstance(item,slice):
            return list(itertools.islice(self._queue,item.start,item.stop,item.step))
        else:
            return self._queue[item]
    
    def __iter__(self):
        return self._queue.__iter__()
    
    def __len__(self):
        return self.qsize()
    
    def clear(self):
        """Clears the queue.Removes every item inside of it."""
        return self._queue.clear()
    
    def remove(self,index:int):
        """Removes the `index`th from the queue.
        
        #### Parameters :
        - `index` : an integer, the index of the element to remove.
        """
        del self._queue[index]

    def get_element(self,index:int):
        """Get an element from the queue, given its index.
        
        #### Parameters :
        - `index` : an integer, the index of the element to return.
        """
        return self._queue[index]
    
    def insert(self,index:int,source):
        """Insert an element into the queue, at `index`.
        
        #### Parameters :
        - `index` : an integer, the index of where `song` will be put.
        - `source` : the element to insert in the queue.
        """
        self._queue.insert(index,source)

    def jump(self,index:int):
        """'Jumps' across the queue. Basically, every element from range 0 to `index` is removed from the queue.
        
        #### Parameters :
        - `index` : an integer, the index of where the queue will now start.

        Example : 

        `lst` is an instance of this class.

        lst = [1,2,3]
        
        lst.jump(2)

        print(lst) #Prints [3]
        """
        for i in range(index - 1):
            self._queue.popleft()

    def shuffle(self):
        """Shuffles the queue."""
        self._queue = random.sample(self._queue,k=len(self))
    
    def remove_range(self,start,end):
        """Removes elements from the queue, such as queue[start,end]
        
        #### Parameters :
        - `start` :  an integer, which is the index of the first element to be removed.
        - `end` : an integer, which is the index of the last element to be removed.
        """
        for i in range(start,end):
            del self._queue[i]
    
    def move(self,song:str,new_index:int):
        """Moves a `song` to a `new_index` in the queue.
        
        #### Parameters :
        - `song` : a string, the title of the song to move to `new_index`.
        - `new_index` : an integer, the new index of the `song`.
        """
        songs_titles = [song["title"] for song in self._queue] #Gets every song title in the queue.
        results = process.extract(song,songs_titles,limit=3) #Extract best ones
        if not results: #In case nothing matches the song
            return None
        index = 0
        maxi = results[0][1]
        for i in range(len(results)): #Results = [('choice',ratio_score),('choice2',ratio_score_2), ...] NOT ordered by ratio_score
            if results[i][1] > maxi:
                maxi = results[i][1]
                index = i
        song_removed = self._queue[index] #To keep track of which song was removed and insert it at the correct index.
        del self._queue[index]
        self.insert(new_index,song_removed)
        return song_removed["title"]
        
        
class MusicPlayer:

    def __init__(self,ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog
        self.queue = CustomQueue(0)
        self.run_next = asyncio.Event()
        self.now_playing = None #Now playing message
        self.volume = .5
        self.current = None
        self.previous = None
        self.loop = None
        ctx.bot.loop.create_task(self.music_player_loop())
    
    async def music_player_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            self.run_next.clear()
            if not self.loop: #Only if we aren't looping the current song
                try:
                    async with timeout(300):
                        source = await self.queue.get()
                        temp = source.copy()
                except asyncio.TimeoutError: #Nothing in queue for 5 minutes, bot disconnects
                    await self._destroy(self._guild)
            else:
                source = self.previous
            source = await YTDLSource.regather_stream(source,loop=self.bot.loop)
            source.volume = self.volume
            self.current = source
            self._guild.voice_client.play(source,after=lambda _:self.bot.loop.call_soon_threadsafe(self.run_next.set)) #Sets the event when the song is done, means it is now not blocking.
            self.now_playing = await self._channel.send(f"Now playing : `{source['title']}`.")
            await self.run_next.wait()
            self.previous = temp
            try:
                await self.now_playing.delete()
            except discord.Forbidden:
                pass
        
    async def _destroy(self,guild):
        return self.bot.loop.create_task(self._cog.cleanup(guild))

class Music(commands.Cog):
    
    def __init__(self,bot:commands.Bot) -> None:
        self.bot = bot
        self.players = {}
        self.white_check = "\U00002705"
        self.red_cross = "\U0000274c"
        self._playlists = {}
        self._playlists_names = {}
        self._songs = {}
        self._urls = set()
        self.bot.loop.create_task(self._cache_playlists())

    async def _cache_playlists(self):
        """Cache playlists informations, in the following structure :
        
        `self._playlists` = {guild_id : {playlist_id : {"playlist_name" : value, "songs" : {song_id1 : {"url" : youtube_url,"title" : song title},song_id2:}}}}

        `self._playlists_names` = {guild_id : {playlist1_name : id1,playlist2_name : id2},guild_id2 : { playlist1_name : id1,playlist2_name : id2,...}

        `self._songs` = {song_name : {"url" : youtube url,"id": id},song2_name : {"url",youtube url 2,"id" : id2}}
        """
        await self.bot.wait_until_ready()
        guilds_ids = [guild.id for guild in self.bot.guilds]
        for guild_id in guilds_ids:
            self._playlists[guild_id] = {}
            self._playlists_names[guild_id] = {}
            async with self.bot.db.execute("SELECT playlist_id,playlist_name FROM playlists WHERE guild_id = ?",(guild_id,)) as cursor:
                playlists_ids_names = [i for i in await cursor.fetchall()]
            playlists_ids = [i[0] for i in playlists_ids_names]
            for playlist in playlists_ids_names:
                self._playlists[guild_id][playlist[0]] = {"playlist_name":playlist[1],"songs":{}}
                self._playlists_names[guild_id][playlist[1]] = playlist[0]
            sql = "SELECT title,url,id FROM songs WHERE id IN (SELECT song_id FROM songs_in_playlists WHERE playlist_id = ? ORDER BY position ASC) "
            for playlist_id in playlists_ids:
                async with self.bot.db.execute(sql,(playlist_id,)) as cursor:
                    songs_infos = await cursor.fetchall()
                for song in songs_infos:
                    self._urls.add(song[1])
                    self._playlists[guild_id][playlist_id]["songs"][song[2]] = {"title":song[0],"url":song[1]}
                    self._songs[song[0]] = {"url":song[1],"id":song[2]}

    def _playlist_exists(self,guild_id,playlist_name : LowerConverter,strict=False):
        """Check if a playlist named `playlist_name` exists.
        
        #### Parameters : 
        - `guild_id` : an integer, which represents a discord.Guild.id.
        - `playlist_name` : a lowercased (through the `LowerConverter` class) string, which represents the playlist name.
        - `strict` : a special case parameter. This is used to see if a playlist **exactly named** `playlist_name` already exists. If set to True, and a playlist doesn't exist,
        this returns None. Default set to False.
        """
        try:
            playlist_id = self._playlists_names[guild_id][playlist_name]
        except KeyError:
            if strict:
                return None
            playlists_names = [i for i in self._playlists_names[guild_id].keys()]
            close_match = process.extractBests(playlist_name,playlists_names,limit=1,score_cutoff=0.7)
            if len(close_match) == 0:
                raise PlaylistNotFound(f"No playlist named `{playlist_name}` was found.")
            else:
                playlist_id = self._playlists_names[guild_id][close_match[0][0]]
                return playlist_id
        else:
            return playlist_id

    def _song_exists(self,guild_id,playlist_id,song_name: LowerConverter,strict=False):
        """Check if a song exists in the cache. Done by caching every song title in the database with their ID.

        Strict parameter has the same objective as in `_playlist_exists` method.
        """
        try:
            song_id = self._songs[song_name]
        except KeyError:
            if strict:
                return None
            songs_infos = [i for i in self._playlists[guild_id][playlist_id]["songs"].values()] #Gets songs' urls and titles
            titles = [i["title"] for i in songs_infos] #only titles
            close_match = process.extractBests(song_name,titles,limit=1,score_cutoff=0.85)
            if len(close_match) == 0:
                raise SongNotFound(f"No song named `{song_name.capitalize()}` was found.")
            else:
                song_id = self._songs[close_match[0][0]]["id"]
        return song_id
    
    def _song_in_playlist(self,guild_id,playlist_id,song_id):
        """Check if the song is in playlist. Done by using IDs only.
        
        #### Parameters :
        - `guild_id` : an integer, which represents a discord.Guild.id.
        - `playlist_id` : an integer, which represents the ID of a playlist in the database.

        """
        try:
            result = self._playlists[guild_id][playlist_id]["songs"][song_id]
        except KeyError:
            raise SongNotInPlaylist("Song not in playlist")
        else:
            return True
    
    def _song_already_stored(self,urls):
        all_urls = [i["url"] for i in self._songs.values()]
        all_ids = [i["id"] for i in self._songs.values()]
        l = []
        index = 0
        for song in urls:
            url = song["webpage_url"]
            if url in all_urls:
                index = all_urls.index(url)
                l.append({"webpage_url":url,"title":song["title"],"id":all_ids[index]})
            else:
                l.append({"webpage_url":url,"title":song["title"]})
            index += 1
        return l

    def _count_songs_from_playlist(self,guild_id,playlist_id):
        """Count songs from a playlist, given the `guild_id` and the `playlist_id`.
        
        #### Parameters : 
        - `guild_id` : an integer, which represents a discord.Guild.id
        - `playlist_id` : an integer, which represents the ID of a playlist in the database.
        """
        return len(self._playlists[guild_id][playlist_id]["songs"]) #is a dict

    async def _get_playlist_creator_id(self,playlist_id):
        """Get the playlist's creator id, given `playlist_id`.
        
        #### Parameters : 
        - `playlist_id` : an integer, which represents the ID of a playlist in a database.
        """
        async with self.bot.db.execute("SELECT creator_id FROM playlists WHERE playlist_id = ?",(playlist_id,)) as cursor:
            result = await cursor.fetchone()
        return result
    
    def _get_last_song_position(self,guild_id,playlist_id):
        """Get the last song position, given `guild_id` and `playlist_id`.

        #### Parameters : 
        - `guild_id` : an integer, which represents a discord.Guild.id
        - `playlist_id` : an integer, which represents the ID of a playlist in the database.
        """
        return len(self._playlists[guild_id][playlist_id]["songs"])

    def _get_playlist_name(self,guild_id,playlist_id):
        """Self explanatory.
        
        #### Parameters : 
        - `guild_id` : an integer, which represents a discord.Guild.id
        - `playlist_id` : an integer, which represents the ID of a playlist in the database.
        """
        return self._playlists[guild_id][playlist_id]["playlist_name"]

    async def _update_songs_position(self,guild_id,playlist_id):
        """Updates the songs position in the database, given the `guild_id` and the `playlist_id`.
        
        #### Parameters : 
        - `guild_id` : an integer, which represents a discord.Guild.id
        - `playlist_id` : an integer, which represents the ID of a playlist in the database.
        """
        songs_ids = [id for id in self._playlists[guild_id][playlist_id].keys()] #Gets songs' IDs from cache
        c = 1 #counter
        for id in songs_ids:
            await self.bot.db.execute("UPDATE songs_in_playlists SET position = ? WHERE playlist_id = ? AND song_id = ?",(c,playlist_id,id)) #Update the songs' positions.
        await self.bot.db.commit()

    def _valid_spotify_playlist_url(self,url):
        """Makes sure the provided spotify playlist URL is a valid one, through regex.

        #### Parameters : 
        - `url`: a string, supposedly a spotify share link.
        
        ### Returns :
        - The playlist URI, found in the link.

        ### Raises :
        - InvalidPlaylistLink : a custom error, to show that the playlist share link is invalid.
        """
        playlist_uri_pattern = re.compile(r"https://open.spotify.com/playlist/(\w{1,30})\?si=\w{1,30}")
        result = playlist_uri_pattern.findall(url)
        if not result :
            raise InvalidPlaylistLink("Playlist URL is invalid. It must looks like : `https://open.spotify.com/playlist/2Uor0e3UQxqCNRKmYpchpV?si=020254f8611b4` (This playlist doesn't exist).")
        return result[0]

    def register_songs(self,songs : list):
        """Extracts data from YTDL, and formats it in a way the bot can easily use.
        
        #### Parameters :
        - `songs` : a list object, where you can find song titles (such as "the witcher 3 blood and wine) or direct YouTube URLs.

        ### Returns :
        - `songs_infos` : a list filled with dicts, with YouTube URL and title of each entries from `songs`.

        ##### Example :
        - `songs_infos` = [{'webpage_url': youtube url here,'title' : title here},{'webpage_url': youtube url2 here,'title' : title here2}]
        """
        songs_infos = []
        for song in songs:
            data = ytdl.extract_info(url=song,download=False)
            if 'entries' in data: #In case `song` isn't a youtube url, extract_info returns a dict of possible results.
                data = data["entries"][0]
            songs_infos.append({'webpage_url': data['webpage_url'],'title': data['title'].lower()})
        return songs_infos

    async def cleanup(self,guild:discord.Guild):
        """Deletes the guild's music player.
        
        #### Parameters : 
        - `guild` : an instance of discord.Guild
        """
        try:
            await guild.voice_client.disconnect()
        except Exception as e:
            print(e)
        try:
            del self.players[guild.id]
        except Exception as e:
            print(e)

    def get_music_player(self,ctx):
        """Returns the guild's music player, or create one if it doesn't exist."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        """When a member leaves, the creator id of playlists they created becomes None."""
        await self.bot.db.execute("UPDATE playlists SET creator_id = ? WHERE creator_id = ?",(None,member.id))
        await self.bot.db.commit()
     
    @commands.command(aliases=["connect"],help="Makes the bot join a specified voice channel or yours (if you're in a voice channel).")
    async def join(self,ctx,*,channel : discord.VoiceChannel=None):
        if channel is None:
            try:
                channel = ctx.author.voice.channel
            except AttributeError: #ctx.author.voice is None if author isn't in a voice channel
                raise AuthorIsNotInVoiceChannel("Either join a voice channel or specify one !")
        if ctx.voice_client: #Bot is already connected to a voice channel
            if ctx.voice_client.channel.id == channel.id: #Wait, the author wants us to join the same voice channel
                return await ctx.send(f"Already connected to {ctx.voice_client.channel.mention}")
            else:
                try:
                    await ctx.voice_client.move_to(channel)
                except asyncio.TimeoutError: #I don't know wtf gone wrong here.
                    return await ctx.send(f"Connection to {channel.mention} somehow failed.")
                else:
                    return await ctx.send(f"Now connected to {channel.mention}.",delete_after=10)
        else: #author inputted a valid voice channel
            try:
                await channel.connect()
            except asyncio.TimeoutError:#I don't know wtf gone wrong here.
                    return await ctx.send(f"Connection to {channel.mention} somehow failed.")
            else:
                return await ctx.send(f"Now connected to {channel.mention}.",delete_after=10)

    @commands.group(aliases=["sing"])
    async def play(self,ctx,*,song):
        await ctx.message.edit(suppress=True) #Avoids integration if user sent a youtube link
        await ctx.trigger_typing()
        if ctx.voice_client is None: #We aren't connected, thus we can't play anything
            await ctx.invoke(self.join)
        try:
            if ctx.voice_client.channel != ctx.author.voice.channel: #Makes sure the bot and the user are in the same voice channel
                raise NotSameVoiceChannel("You must be in my voice channel to add a song to the queue !")
        except AttributeError: #Author isn't in a voice channel, because we made sure bot is in one.
            raise AuthorIsNotInVoiceChannel("You're not in a voice channel (and to be even more accurate, the voice channel I'm connected to), so you can't use this command.")
        player = self.get_music_player(ctx)
        source = await YTDLSource.create_source(ctx,song,loop=self.bot.loop,download=False) #Creates the source for the song to be played
        await player.queue.put(source)
    
    @commands.command(aliases=["playprev"],help="Plays the previous song AFTER the current one is done. Doesn't play anything if there are no previous song, obviously.")
    async def playprevious(self,ctx):
        player = self.get_music_player(ctx)
        if player.previous is None:
            return await ctx.send("Wait. I didn't play anything before the current song.")
        player.queue.insert(0,player.previous)
        title = player.previous["title"]
        return await ctx.send(f"`{title}` will be played again after the current song.")

    async def play_playlist(self,ctx,songs_list):
        """Internal process. Adds the songs to the queue"""
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
            source = await YTDLSource.create_source(ctx,song["url"],loop=self.bot.loop,download=False,playlist=True)
            await player.queue.put(source)

    @commands.command(help="Bot disconnects from voice channel. ")
    async def stop(self,ctx):
        await self.cleanup(ctx.guild)
        return await ctx.send("Disconnected.")

    @commands.command(help="Wait, you really need help for that ? Pauses the current song.")
    async def pause(self,ctx):
        if ctx.voice_client.is_paused():
            return await ctx.send("The song is already paused.")
        ctx.voice_client.pause()
        return await ctx.send(f"Song paused. (requested by {ctx.author.mention})",allowed_mentions=self.bot.no_mentions)

    @commands.command(help="Skips the song, only if the majority of people listening to it wants to. Skips it without a vote if you're alone in the voice channel.")
    async def skip(self,ctx):
        if not ctx.voice_client.is_playing(): #Self explanatory
            return await ctx.send("I'm not playing anything.")
        player = self.get_music_player(ctx) #Music player for ctx.guild
        if player.queue.empty(): #Nothing to skip if queue is empty
            return await ctx.send("Current queue is empty.")
        voice_client_channel = ctx.voice_client.channel
        voice_channel_members = [member for member in voice_client_channel.members if not member.bot] #Gets every member in the bot's voice channel, that aren't bots.
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
        if r is None: #Vote message not in cache neither could be fetched from the channel (most likely was deleted)
            return await ctx.send("An error occured. Please restart the poll. (the vote message was most likely deleted)")
        reactions_count = []
        for reaction in r.reactions:
            try:
                reactions_count.append((reaction.emoji,len([member for member in await reaction.users().flatten() if not member.bot and member.voice.channel == ctx.voice_client.channel]))) #adds the reaction and the number of people who reacted to it. (BOTS AND MEMBERS NOT IN VC ARE EXCLUDED)
            except AttributeError: #Member.voice is None, so member.voice.channel raises this error. Means someone who voted wasn't in a voice channel at the time.
                continue
        maxi = max(reactions_count,key=lambda item:item[1])
        if maxi[1] == 0:
            return await ctx.send("Well, no one voted. What do I do now..")
        elif maxi[0] == "✅": #Skipping
            await ctx.send(f"Skipping song ({maxi[1]} votes).")
            ctx.voice_client.stop()
        else: #Not skipping
            return await ctx.send(f"I hate democracy ({maxi[1]} votes).")

    @commands.command(help="Resumes a paused song.")
    async def resume(self,ctx):
        if ctx.voice_client.is_playing():
            return await ctx.send("I'm already playing something !")
        ctx.voice_client.resume()
        return await ctx.send(f"Song resumed. (requested by {ctx.author.mention})",allowed_mentions=self.bot.no_mentions,delete_after=10)

    @commands.group(invoke_without_command=True,help="Shows the server's songs queue.")
    async def queue(self,ctx):
        if ctx.invoked_subcommand is None:
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

    @queue.command(help="Clears the server's songs queue.")
    async def clear(self,ctx):
        player = self.get_music_player(ctx)
        if not len(player.queue):
            return await ctx.send("Current queue is already empty.")
        player.queue.clear()
        return await ctx.send("Cleared the queue.")

    @queue.group(aliases=["delete"],help="Removes the songs at the `index` index.",brief="To remove the 2nd song of the queue, you would use `$queue remove 2`.")
    async def remove(self,ctx,index:int):
        if index < 1:
            return await ctx.send("A song index cannot be lower than 1. How could I delete a song that doesn't exist ?")
        player = self.get_music_player(ctx)
        if len(player.queue) == 0:
            return await ctx.send("The queue is empty. You want me to remove the emptiness of it ?")
        song_removed = player.queue.get_element(index - 1)
        player.queue.remove(index - 1)
        return await ctx.send(f"Removed `{song_removed['title']}` from the queue.")

    @remove.command(help="Removes songs from index `start` to `end` included.",brief="To remove songs from index 2 to 4, you would use `$queue remove range 2:4`.")
    async def range(self,ctx,slice:SliceConverter):
        player = self.get_music_player(ctx)
        l = player.queue
        if not l:
            return await ctx.send("Current queue is empty.You want me to remove the emptiness of it ?")
        start,end = slice
        if start < 0:
            start = 0
        if end >= l:
            end = l
        player.queue.remove_range(start,end)
        return await ctx.send(f"Removed songs from index {start} to {end} ({end - start + 1} songs).")

    @queue.command(help="Insert a song at the given position in the queue.",brief="To insert a song at index 1 (so the song will be played right after the current one is done), you would use `$queue insert 1 mysong`.")
    async def insert(self,ctx,index:int,*,song):
        await ctx.message.edit(suppress=True)
        player = self.get_music_player(ctx)
        if index < 1:
            index = 0
        elif index > len(player.queue):
            index = len(player.queue)
        source = await YTDLSource.create_source(ctx,search=song,loop=self.bot.loop)
        player.queue.insert(index - 1,source)
        return await ctx.send(f"Inserted `{source['title']}` at index {index} of this queue.")
    
    @queue.command(help="Basically, the queue makes a jump to the index you want. This means it skips all songs between next song and `index`th song.")
    async def jump(self,ctx,index:int):
        player = self.get_music_player(ctx)
        l = len(player.queue)
        if index < 1:
            index = 1
        elif index > l:
            index = l
        player.queue.jump(index)
        ctx.voice_client.stop()
        return await ctx.send(f"Jumped to `{player.queue._queue[0]['title']}`")

    @queue.command(help="Shuffles the queue. Unexpected, I know.")
    async def shuffle(self,ctx):
        player = self.get_music_player(ctx)
        if len(player.queue) == 0: #Can't shuffle an empty queue.
            return await ctx.send("Current queue is empty.")
        player.queue.shuffle()
        return await ctx.send("Shuffled the queue !")

    @queue.command(help="Moves the song to a new index in the queue.",brief="`$queue move 3 mysongnameherewhichisdope` would move 'mysongnameherewhichisdope' to index 3.")
    async def move(self,ctx,new_index:int,*,title):
        player = self.get_music_player(ctx)
        l = len(player.queue)
        if l == 0:
            return await ctx.send("Current queue is empty.")
        if new_index < 1:
            new_index = 1
        elif new_index >= l:
            new_index = l
        song_moved = player.queue.move(title,new_index - 1)
        if song_moved is None:
            return await ctx.send(f"No song named `{title}` was found.")
        return await ctx.send(f"Succesfully moved `{song_moved}` to index {new_index}.")

    @queue.command(help="Loops the currently playing song.",brief="Do you really need an example on how to type `$queue loop` ?")
    async def loop(self,ctx):
        player = self.get_music_player(ctx)
        if not ctx.voice_client.is_playing():
            return await ctx.send("I'm currently not playing anything.")
        player.loop = not player.loop
        if player.loop:
            return await ctx.send("Looping the current song.")
        return await ctx.send("Removing the loop on the current song.")

    @commands.command(help="Allows you to change the volume of the music the bot is playing. Accepts value between 0 and 100, default is 50.",brief="`$volume 30` sets the volume to 30%.Pure magic.")
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

    @commands.command(help="Shows the playlists available on this server. To know more about each of them, use `$playlist info [aplaylistname]`.",brief="Tell me you don't need help for that. Please.")
    async def playlists(self,ctx):
        playlists_list = []
        em = discord.Embed(title=f"{ctx.guild}'s playlists !",color=discord.Colour.blurple())
        playlists_ids = [playlist_id for playlist_id in self._playlists[ctx.guild.id].keys()] #see how self._playlists is structured to understand faster
        for id in playlists_ids:
            number_of_songs = self._count_songs_from_playlist(ctx.guild.id,id)
            playlist_name = self._get_playlist_name(ctx.guild.id,id)
            playlists_list.append(f"`- {playlist_name} ({number_of_songs} songs).`")
        if len(playlists_list) == 0:
            em.description = "Woah. Emptiness."
            return await ctx.send(embed=em)
        elif len(playlists_list) < 10:
            em.description = "\n".join(playlists_list)
            return await ctx.send(embed=em)
        else:
            menu = menus.MenuPages(PlaylistsDisplayer(playlists_list,per_page=10)) #Menus in case we have >= 10 playlists
            return await menu.start(ctx)

    @commands.group(invoke_without_command=True,help="Starts to play a playlist. (if the playlist does exist)",brief="`$playlist myplaylistnameheredopeaf` will play the playlist named `myplaylistnameheredopeaf`")
    async def playlist(self,ctx,*,playlist_name):
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        playlist_songs = [i for i in self._playlists[ctx.guild.id][playlist_exists]["songs"].values()]
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        await self.play_playlist(ctx,playlist_songs)
        await ctx.send(f"Let's go ! I will play the songs of `{actual_playlist_name}` playlist.")

    @playlist.command(aliases=['new'],help="Allows you to create a new playlist. /!\ Playlist name and songs titles MUST be quoted if they have more than a single word.",
    brief="`$playlist create 'dope playlist' 'nice song' 'very good song' 'great song'` will create a playlist named `dope playlist` with the songs in.")
    async def create(self,ctx,*args):
        await ctx.message.edit(suppress=True)
        if len(args) == 0:
            return await ctx.send("You didn't give me a playlist name.")
        playlist_exists = self._playlist_exists(ctx.guild.id,args[0],strict=True)
        if playlist_exists:
            return await ctx.send(f"A playlist named `{args[0]}` already exists.")
        playlist_created = await self.bot.db.execute_insert("INSERT INTO playlists(playlist_name,creator_id,guild_id) VALUES(?,?,?)",(args[0].lower(),ctx.author.id,ctx.guild.id))
        await self.bot.db.commit()
        new_playlist_id = playlist_created[0]
        self._playlists[ctx.guild.id][new_playlist_id] = {"playlist_name":args[0],"songs":{}}
        self._playlists_names[ctx.guild.id][args[0].lower()] = new_playlist_id
        if len(args) > 1:
            nb_songs = len(args) - 1
            await ctx.send(f"Pshhh. Be patient, I need to register {nb_songs} songs.",delete_after=5)
            f = partial(self.register_songs,args[1:])
            songs_list = await self.bot.loop.run_in_executor(None,f)
            songs_list = self._song_already_stored(songs_list)
            sql = "INSERT INTO songs(title,url) VALUES(?,?)"
            counter = 1
            for song in songs_list:
                try:
                    new_song_id = song["id"]
                except KeyError:
                    song_inserted = await self.bot.db.execute_insert(sql,(song["title"].lower(),song["webpage_url"]))
                    new_song_id = song_inserted[0]
                await self.bot.db.execute("INSERT INTO songs_in_playlists(playlist_id,song_id,position) VALUES(?,?,?)",(new_playlist_id,new_song_id,counter))
                self._playlists[ctx.guild.id][new_playlist_id]["songs"][new_song_id] = {"url":song["webpage_url"],"title":song["title"]}
                self._songs[song["title"]] = {"url":song["webpage_url"],"id":new_song_id}
                counter += 1
            await self.bot.db.commit()
        return await ctx.send((f"Successfully created playlist `{args[0]}`." if len(args) == 1 else f"Successfully created playlist `{args[0]}`. ({len(songs_list)} songs)"))

    @playlist.command(aliases=["remove"],help="Lets you delete a playlist. You must either have 'manage server' permissions or be the creator of this playlist.",
    brief="`$playlist delete playlistnamehere` will delete the playlist named `playlistnamehere`.")
    async def delete(self,ctx,*,playlist_name):
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        creator_id = await self._get_playlist_creator_id(playlist_exists)
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        if not(creator_id is None or creator_id[0] == ctx.author.id or ctx.author.guild_permissions.manage_guild):
            return await ctx.send("This playlist has a owner. And you're not the owner. Neither do you have the `manage server` permissions. Thus you can't delete this playlist.")
        try:
            await ctx.send(f"Are you sure you want to delete the `{actual_playlist_name}` playlist ? No way to go back !")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute("DELETE FROM songs_in_playlists WHERE playlist_id = ?",(playlist_exists,))
                await self.bot.db.execute("DELETE FROM playlists WHERE playlist_id = ?",(playlist_exists,))
                await self.bot.db.commit()
                del self._playlists[ctx.guild.id][playlist_exists]
                del self._playlists_names[ctx.guild.id][actual_playlist_name]
                return await ctx.send(f"Done ! Playlist `{actual_playlist_name}` was deleted.")
            else:
                return await ctx.send("Aborting process.")

    @playlist.command(help="Lets you edit the name of a playlist.\n /!\ Old playlist name must be quoted if it isn't a single word.",
    brief="`$playlist edit 'trash playlist' my new great playlist` \nThis changes the name of the playlist to `my new great playlist`.")
    async def edit(self,ctx,playlist_name,*,new_playlist_name):
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        creator_id = await self._get_playlist_creator_id(playlist_exists)
        if not(creator_id is None or creator_id[0] == ctx.author.id or ctx.author.guild_permissions.manage_guild):
            return await ctx.send("This playlist has a owner. And you're not the owner. Neither do you have the `manage server` permissions. Thus you can't delete this playlist.")
        await self.bot.db.execute("UPDATE playlists SET playlist_name = ? WHERE playlist_id = ?",(new_playlist_name.lower(),playlist_exists))
        await self.bot.db.commit()
        del self._playlists[ctx.guild.id][playlist_name]
        self._playlists[ctx.guild.id][new_playlist_name] = playlist_exists
        self._playlists_name[playlist_exists] = new_playlist_name
        return await ctx.send(f"Playlist name changed : `{actual_playlist_name}` -> `{new_playlist_name}`.")

    @playlist.command(aliases=["infos"],help="Gives you informations about the desired playlist, such as the songs that are in the playlist, the creator of this playlist and when it was created.",
    brief="`$playlist info my favourite playlist`")
    async def info(self,ctx,*,playlist_name):
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        playlist_id = playlist_exists
        async with self.bot.db.execute("SELECT creator_id,created_at FROM playlists WHERE playlist_id = ?",(playlist_id,)) as cursor:
            playlist_infos = await cursor.fetchone()
        sql = "SELECT url,title FROM songs WHERE id IN (SELECT song_id FROM songs_in_playlists WHERE playlist_id = ?)"
        async with self.bot.db.execute(sql,(playlist_id,)) as cursor:
            playlist_songs = [f"- [`{song[1].capitalize()}`]({song[0]})" for song in await cursor.fetchall()]
        creator = ctx.guild.get_member(playlist_infos[0]) or "Creator left the server."
        datetime_object = datetime.datetime.strptime(playlist_infos[1],"%Y-%m-%d %H:%M:%S")
        timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
        if len(playlist_songs) <= 10:
            datetime_object = datetime.datetime.strptime(playlist_infos[1],"%Y-%m-%d %H:%M:%S")
            timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
            em = discord.Embed(title=f"'{actual_playlist_name}' playlist - {len(playlist_songs)} songs.",description="\n".join(playlist_songs))
            em.add_field(name="Created at :",value=f"<t:{timestamp}:f>")
            em.add_field(name="Creator :",value=creator.mention)
            return await ctx.send(embed=em)
        menu = menus.MenuPages(PlaylistInfosDisplayer(playlist_songs,per_page=10,tp=timestamp,author=creator,title=actual_playlist_name))
        return await menu.start(ctx)
    
    @playlist.command(aliases=["addsong"],help="Lets you add song(s) to a playlist.\n /!\ Playlist name AND songs titles MUST be quoted if they aren't a single word.",
    brief="`$playlist addsongs 'my favorite playlist' 'the witcher 3 on the champs désolés' 'radioactive imagine dragons'`")
    async def addsongs(self,ctx,playlist_name,*songs):
        await ctx.message.edit(suppress=True)
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        playlist_id = playlist_exists
        f = partial(self.register_songs,songs)
        songs_to_add = await self.bot.loop.run_in_executor(None,f)
        songs_to_add = self._song_already_stored(songs_to_add)
        sql = "INSERT INTO songs(title,url) VALUES(?,?)"
        last_song_position = self._get_last_song_position(ctx.guild.id,playlist_id)
        song_position = last_song_position + 1
        for song in songs_to_add:
            try:
                new_song_id = song["id"]
            except KeyError:
                song_inserted = await self.bot.db.execute_insert(sql,(song["title"].lower(),song["webpage_url"]))
                new_song_id = song_inserted[0]
                self._songs[song["title"]] = {"url":song["webpage_url"],"id":new_song_id}
            await self.bot.db.execute("INSERT INTO songs_in_playlists(playlist_id,song_id,position) VALUES(?,?,?)",(playlist_exists,new_song_id,song_position))
            self._playlists[ctx.guild.id][playlist_exists]["songs"][new_song_id] = {"url":song["webpage_url"],"title":song["title"]}
            song_position += 1
        await self.bot.db.commit()
        return await ctx.send((f"Successfully added the songs. (`{playlist_name}` playlist)" if len(song) > 1 else f"Successfully added the song (`{playlist_name}` playlist)"))

    @playlist.command(aliases=["removesong"],help="Lets you delete a song from a playlist.\n /!\ Playlist name must be quoted if it isn't a single word.",
    brief="$playlist delsong 'new favorite playlist' trash song")
    async def delsong(self,ctx,playlist_name,*,song_name):
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        song_exists = self._song_exists(ctx.guild.id,playlist_exists,song_name)
        is_song_in_playlist = self._song_in_playlist(ctx.guild.id,playlist_exists,song_exists)
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        actual_song_name = self._playlists[ctx.guild.id][playlist_exists]["songs"][song_exists]["title"]
        try:
            await ctx.send(f"Are you sure you want to remove `{actual_song_name}` from `{actual_playlist_name}` playlist ?")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute("DELETE FROM songs_in_playlists WHERE playlist_id = ? AND song_id = ?",(playlist_exists,song_exists))
                await self.bot.db.commit()
                del self._playlists[ctx.guild.id][playlist_exists]["songs"][song_exists]
                return await ctx.send(f"Successfully removed `{actual_song_name}` from `{actual_playlist_name}` playlist ?")
            else:
                return await ctx.send("Well, now I'm not doing it.")

    @playlist.command(aliases=["removefrom"],help="Deletes every song from `index` position to the end of the playlist.\n /!\ Playlist name must be quoted if it isn't a single word.",
    brief="`$playlist delfrom 'my best playlist' 3` will delete every song that comes after the third song of the playlist.")
    async def delfrom(self,ctx,playlist_name,index:int):
        if index < 0:
            return await ctx.send("... I can't process negative numbers here.")
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        number_of_songs = self._count_songs_from_playlist(ctx.guild.id,playlist_exists)
        if index > number_of_songs:
            return await ctx.send(f"Wait. You want to delete songs that comes after the first {index} songs, but the playlist only contains {number_of_songs} songs.")
        await self.bot.db.execute("DELETE FROM songs_in_playlists WHERE position >= ?",(index,))
        await self.bot.db.commit()
        songs = [i for i in self._playlists[ctx.guild.id][playlist_exists]["songs"].items()]
        for i in range(index-1,len(songs)):
            song_id = songs[i][0]
            del self._playlists[ctx.guild.id][playlist_exists]["songs"][song_id]
        await self._update_songs_position(ctx.guild.id,playlist_exists)
        return await ctx.send(f"Successfully removed every last {number_of_songs - index} songs.")
    
    @playlist.command(aliases=["removeto"],help="Deletes every song from start to `index` position of the playlist.\n /!\ Playlist name must be quoted if it isn't a single word.",
    brief="`$playlist delto 'my best playlist' 3` will delete every song that is before the third song of the playlist.")
    async def delto(self,ctx,playlist_name,n:int):
        if n < 0:
            return await ctx.send("... I can't process negative numbers here.")
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        number_of_songs = self._count_songs_from_playlist(ctx.guild.id,playlist_exists)
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        if n > number_of_songs:
            n = number_of_songs
        try:
            await ctx.send(f"Are you sure you want to delete {n} songs from the `{actual_playlist_name}` ? No coming back !")
            m = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            await self.bot.db.execute("DELETE FROM songs_in_playlists WHERE position <= ?",(n,))
            await self.bot.db.commit()
            songs = [i for i in self._playlists[ctx.guild.id][playlist_exists]["songs"].items()]
            for i in range(n):
                song_id = songs[i][0]
                del self._playlists[ctx.guild.id][playlist_exists]["songs"][song_id]
            await self._update_songs_position(ctx.guild.id,playlist_exists)
            return await ctx.send(f"Successfully removed first {number_of_songs - n} songs.")
    
    @playlist.command(aliases=["removefromto"],help="This is a mix of delfrom and delto. Lets you remove every song between two indexes !\n /!\ Playlist name must be quoted if it isn't a single word.",
    brief="`$playlist delfromto 'my greatest playlist' 2:4` will remove the 2nd,3rd and 4th songs from the playlist.")
    async def delfromto(self,ctx,playlist_name,slice:SliceConverter):
        start,end = slice
        playlist_exists = self._playlist_exists(ctx.guild.id,playlist_name)
        number_of_songs = self._count_songs_from_playlist(ctx.guild.id,playlist_exists)
        actual_playlist_name = self._playlists[ctx.guild.id][playlist_exists]["playlist_name"]
        if start < 1:
            start = 0
        if end > number_of_songs:
            end = number_of_songs
        try:
            await ctx.send(f"Are you sure you want to delete {end - start} songs from the `{actual_playlist_name}` ? No coming back !")
            m = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            await self.bot.db.execute("DELETE FROM songs_in_playlists WHERE position >= ? AND position <= ?",(start,end))
            await self.bot.db.commit()
            songs = [i for i in self._playlists[ctx.guild.id][playlist_exists]["songs"].items()]
            for i in range(start,end+1):
                song_id = songs[i][0]
                del self._playlists[ctx.guild.id][playlist_exists]["songs"][song_id]
            await self._update_songs_position(ctx.guild.id,playlist_exists)
            return await ctx.send(f"Deleted {end - start + 1} (index {start} to {end}).")

    @commands.group(invoke_without_command=True,help="Lets you play a playlist that you have on Spotify. The playlist MUST be public or collaborative. It may take time if the playlist is very big.",
    brief="`$spotify spotifyplaylistsharelinkhere` will play the desired Spotify playlist !")
    async def spotify(self,ctx,url):
        await ctx.message.edit(suppress=True)
        await ctx.trigger_typing()
        playlist_songs = []
        playlist_uri = self._valid_spotify_playlist_url(url)
        auth = asyncspotify.ClientCredentialsFlow(SPOTIFY_CLIENT_ID,SPOTIFY_CLIENT_SECRET)
        async with asyncspotify.Client(auth) as sp:
            try:
                playlist = await self.bot.sp.get_playlist(playlist_uri)
            except asyncspotify.NotFound:
                return await ctx.send("Playlist not found. Make sure it is public/collaborative, and double check the shareable link !")
            else:
                async for track in playlist:
                    playlist_songs.append({"url":f"{track.name} {track.artists}"})
        await ctx.send("I'm getting the tracks in the playlist from Spotify, wait !")
        return await self.play_playlist(ctx,playlist_songs)
    
    @spotify.command(aliases=["savep","sp"],help="Lets you save a Spotify playlist.The playlist MUST be public or collaborative.It may take time if the playlist is very big.",
    brief="`$spotify saveplaylist spotifyplaylistsharelinkhere` will save the playlist to your server (available later as a normal bot playlist).")
    async def saveplaylist(self,ctx,url):
        await ctx.trigger_typing()
        playlist_uri = self._valid_spotify_playlist_url(url)
        playlist_songs = []
        auth = asyncspotify.ClientCredentialsFlow(SPOTIFY_CLIENT_ID,SPOTIFY_CLIENT_SECRET)
        async with asyncspotify.Client(auth) as sp:
            try:
                playlist = await sp.get_playlist(playlist_uri)
            except asyncspotify.NotFound:
                return await ctx.send("Playlist not found. Make sure it is public/collaborative, and double check the shareable link !")
            else:
                playlist_songs.append(playlist.name)
                async for track in playlist:
                    playlist_songs.append(f"{track.name} {track.artists}")
        await self.create(ctx,*playlist_songs)

    @pause.before_invoke
    @stop.before_invoke
    @resume.before_invoke
    @skip.before_invoke
    @volume.before_invoke
    @loop.before_invoke
    @remove.before_invoke
    @insert.before_invoke
    @playprevious.before_invoke
    @shuffle.before_invoke
    async def ensure_same_voice_channel(self,ctx):
        if ctx.voice_client is None:
            raise NoVoiceClient("I'm currently not connected to a voice channel.")        
        try:
            author_vc = ctx.author.voice.channel
        except AttributeError: #Author isn't in a voice channel
            raise AuthorIsNotInVoiceChannel("You must be connected to a voice channel (actually, my voice channel) to use this command.")
        else:
            if author_vc != ctx.voice_client.channel: #Author isn't in the same voice channel as bot
                raise NotSameVoiceChannel("You must be connected to my voice channel to use this command.")

def setup(bot):
    bot.add_cog(Music(bot))