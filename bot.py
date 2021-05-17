from discord import colour
from discord.errors import Forbidden
from dotenv import load_dotenv
import discord
import os
from discord.ext import commands
import requests
import asyncio
import youtube_dl
import aiosqlite
from difflib import get_close_matches

load_dotenv()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"),description="A Chuck Norris dedicated discord bot !",intents=discord.Intents.all())
TOKEN = os.getenv('BOT_TOKEN') #Bot token needs to be stored in a .env file

ydl_opts = {
    'format':"bestaudio/best",
    "postprocessors":[{
        'key':'FFmpegExtractAudio',
        'preferredcodec':'mp3',
        'preferredquality':'256'
    }]
}
ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}


class ChuckNorris(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=["cn","nc"])
    async def chucknorris(self,ctx,*args):#chuck norris joke will be send to the channel
        l = len(args)
        try:
            if l > 0:
                r = requests.get(f"https://api.chucknorris.io/jokes/random?category={args[0].lower()}")
            else:
                r = requests.get("https://api.chucknorris.io/jokes/random")
            joke = r.json()["value"]
            categories = ",".join(r.json()["categories"]) if len(r.json()["categories"]) > 0 else "None"
            embedVar = discord.Embed(title=f"Categories : {categories}.",color=0xaaffaa)
            embedVar.add_field(name="This joke is provided to you by : Chuck Norris himself.",value=f"{joke}")
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        except KeyError:
            embedVar = discord.Embed(title=f'There are no such categories as "{args[0]}".',color=0xff0000)
            embedVar.add_field(name="Don't try to fool me, I'll know it.",value="I'm also telling Chuck Norris about this. Watch your back.")
            embedVar.set_image(url="https://voi.img.pmdstatic.net/fit/http.3A.2F.2Fprd2-bone-image.2Es3-website-eu-west-1.2Eamazonaws.2Ecom.2Fvoi.2Fvar.2Fvoi.2Fstorage.2Fimages.2Fmedia.2Fmultiupload-du-25-juillet-2013.2Fchuck-norris-pl.2F8633422-1-fre-FR.2Fchuck-norris-pl.2Ejpg/460x258/quality/80/chuck-norris-vend-la-maison-qui-a-servi-de-decor-a-walker-texas-ranger.jpg")
            embedVar.set_footer(text="Pshhh. If you have no clue what categories are available, type '$ckcategories' !")
            await ctx.send(embed=embedVar)
    
    @commands.command(aliases=["cncat","cnc","cncategoires"])
    async def cncategories(self,ctx):
        embedVar = discord.Embed(title="The categories of joke the bot can tell you.",color=0xaaffaa)
        r = requests.get("https://api.chucknorris.io/jokes/categories")
        embedVar.add_field(name="Pick your favourite ! ",value="\n".join(["• {}".format(i) for i in r.json()]))
        await ctx.send(embed=embedVar)

class Moderation(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        """Create the role muted as soon as the bot joins the guild, if no muted role exists. Disable send messages permissions and speak permissions for muted role in every channel"""
        for role in guild.roles:
            if role.name.lower() == "muted":
                return
        mutedRole = await guild.create_role(name="Muted",permissions=discord.Permissions(send_messages=False,speak=False))
        for channel in guild.channels:
            await channel.set_permissions(mutedRole, send_messages = False, speak = False)
    
    @commands.command(aliases=["addrole","roleadd"])
    @commands.has_permissions(manage_roles=True)
    async def giverole(self,ctx,member:discord.Member,role:discord.Role):
        await member.add_roles(role)
        embedVar = discord.Embed(description=f"{member} was granted the {role} role.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["rmvrole"])
    @commands.has_permissions(manage_roles = True)
    async def removerole(self,ctx,member : discord.Member, role:discord.Role): # $removerole [member] [role]
        await member.remove_roles(role)
        embedVar = discord.Embed(description=f"{member} lost the {role} role.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["gtfo"])
    @commands.has_permissions(kick_members = True)
    async def kick(self,ctx, member: discord.Member, *,reason="Not specified."): # $kick [member] [reason]
        PMembed = discord.Embed(title="Uh oh. Looks like you did something quite bad !",color=0xff0000)
        PMembed.add_field(name=f"You were kicked from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
        await member.send(embed=PMembed)
        await member.kick(reason=reason)
        embedVar = discord.Embed(description=f"{member} was successfully kicked from the server.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_permissions()
    async def mute(self,ctx,member:discord.Member,time:str=None):
        mutedRole = [role for role in ctx.guild.roles if role.name == "Muted"][0]
        await member.add_roles(mutedRole)
        if time is not None:
            await asyncio.sleep(int(time))
            await member.remove_roles(mutedRole)
    
    @commands.command(aliases=["demute"])
    @commands.has_permissions()
    async def unmute(self,ctx,user:discord.Member):
        mutedRole = [role for role in ctx.guild.roles if role.name == "Muted"][0]
        await user.remove_roles(mutedRole)

    @commands.command(aliases=["banl","bl"])
    @commands.has_permissions(administrator = True)
    async def banlist(self,ctx): #Displays current banlist from the server
        bans = await ctx.guild.bans()
        if len(bans) == 0:
            embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        else:
            embedVar = discord.Embed(title="Here are all the people banned on this server : ",color=0xaaffaa)
            pretty_list = ["• {}#{} for : {} ".format(entry.user.name,entry.user.discriminator,entry[0]) for entry in bans]
            embedVar.add_field(name=f"There are {len(pretty_list)} of them ! ",value="\n".join(pretty_list))
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)

    @commands.command(aliases=["b","bna"])
    @commands.has_permissions(ban_members = True)
    async def ban(self,ctx,member : discord.Member,time:str=None, *,reason="Not specified."): # $ban [member] [reason]
        embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
        embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await member.send(embed=embedVar)
        await member.ban(reason=reason)
        if time is not None:
            await asyncio.sleep(int(time))
            await ctx.guild.unban(member,reason="Ban duration is over.")

    @commands.command(aliases=["u","unbna"])
    @commands.has_permissions(ban_members = True)
    async def unban(self,ctx,person,*,reason="Not specified."):
        bans = await ctx.guild.bans()
        if len(bans) == 0:
            embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
            return await ctx.send(embed=embedVar)
        elif person == "all":
            for entry in bans:
                user = await bot.fetch_user(entry.user.id)
                await ctx.guild.unban(user)
                embedVar = discord.Embed(title="All members have been successfully unbanned !",color=0xaaffaa)
                return await ctx.send(embed=embedVar)
        count = 0
        dictionary = dict()
        string = ""
        continuer = True
        for entry in bans:
            if "{0.name}#{0.discriminator}".format(entry.user) == person:
                user = await bot.fetch_user(entry.user.id)
                embedVar = discord.Embed(title="{0.name}#{0.discriminator} is now free to join us again !".format(entry.user),color=0xaaffaa)
                embedVar.set_footer(text=f"Requested by {ctx.author}.")
                await ctx.send(embed=embedVar)
                return await ctx.guild.unban(user,reason=reason)
            elif entry.user.name == person:
                    count += 1
                    key = f"{count}- {entry.user.name}#{entry.user.discriminator}"
                    dictionary[key] = entry.user.id
                    string += f"{key}\n"
        if continuer:
            if count >= 1:
                embedVar = discord.Embed(title=f"Uh oh. According to what you gave me, '{person}', I found {count} {'person' if count == 1 else 'people'} named like this.",color=0xaaaaff)
                embedVar.add_field(name="Here is the list of them : ",value=string)
                embedVar.add_field(name="How to pick the person you want to unban ?",value="Just give me the number before their name !")
                embedVar.set_footer(text=f"Requested by {ctx.author}.")
                await ctx.send(embed=embedVar)   
                def check(m):
                    return m.author == ctx.author 
                ans = await bot.wait_for('message',check=check, timeout=10)
                try:
                    emoji = '\u2705'
                    lines = string.split("\n")
                    identifier = int(dictionary[lines[int("{0.content}".format(ans)) - 1]])
                    user = await bot.fetch_user(identifier)
                    await ctx.guild.unban(user)
                    await ans.add_reaction(emoji)
                    embedVar = discord.Embed(title="{0.name}#{0.discriminator} is now free to join us again !".format(user),color=0xaaffaa)
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await ctx.send(embed=embedVar)
                except:
                    emoji = '\u2705'
                    embedVar = discord.Embed(title="Uh oh. Something went wrong.",color=0xffaaaa)
                    embedVar.add_field(name="For some reasons, I couldn't unban the user you selected.",value="Please try again !")
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await ctx.send(embed=embedVar)
            else:
                await ctx.send("I can't find anyone with username '{}'. Try something else !".format(person))

    @commands.command(aliases=["p","perrms"])
    @commands.has_permissions(administrator = True)
    async def perms(self,ctx,member:discord.Member):
        embedVar = discord.Embed(title=f"You asked for {member}'s permissions on {ctx.guild}.",color=0xaaaaff)
        embedVar.add_field(name="Here they are : ",value="\n".join(["• {}".format(i[0]) for i in member.guild_permissions if i[1] is True]))
        await ctx.author.send(embed=embedVar)

    @commands.command(aliases=["clear","clearmsg"])
    @commands.has_permissions(manage_messages = True) 
    async def purge(self,ctx,Amount:int=2): #Delete "Amount" messages from the current channel. $purge [int]
        await ctx.channel.purge(limit=Amount + 1)

class Music(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    def already_connected_or_playing(self,c:commands.Context):
        return (c.voice_client is None or c.voice_client.is_playing() is False) and c.author.voice is not None
            
    @commands.command(aliases=["song"])
    async def play(self,ctx,url:str):
        if self.already_connected_or_playing(ctx):
            channel = ctx.author.voice.channel
            await channel.connect()
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                song_info = ydl.extract_info(url, download=False)
            embedVar = discord.Embed(title="Now playing...",color=0xaaaaff,description=song_info["title"])
            await ctx.send(embed=embedVar)
            ctx.guild.voice_client.play(discord.FFmpegPCMAudio(song_info["formats"][0]["url"]))
            ctx.guild.voice_client.source = discord.PCMVolumeTransformer(ctx.guild.voice_client.source)
            ctx.guild.voice_client.source.volume = 1
        else:
            await ctx.message.delete()
            embedVar = discord.Embed(title="Uh oh. Something went wrong.",color=0xff0000,description="I can't be in two voice channels at the same time. Please wait until I'm available !")
            await ctx.send(embed=embedVar)

    @commands.command(aliases=["disconnect"])
    async def leave(self,ctx):
        await ctx.voice_client.disconnect()
    
    @commands.command()
    async def pause(self,ctx):
        await ctx.voice_client.pause()
    
    @commands.command()
    async def resume(self,ctx):
        await ctx.voice_client.resume()

    @commands.command()
    async def stop(self,ctx):
        ctx.voice_client.stop()


class Tags(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"CREATE TABLE IF NOT EXISTS _{str(guild.id)}(tag_name TEXT,description TEXT);")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"DROP TABLE _{str(guild.id)};")
            await db.commit()
    
    @commands.group(invoke_without_command=True)
    async def tag(self,ctx,*,tag_name):
        guild_id = f"_{str(ctx.guild.id)}"
        if ctx.invoked_subcommand is None:
            async with aiosqlite.connect("databases/tags.db") as db:
                async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = '{tag_name}';") as cursor:
                    desc = await cursor.fetchone()
                    if desc is not None:
                        await ctx.send(desc[0])
                    else:
                        tag_names_availables = await db.execute(f"SELECT tag_name FROM {guild_id}")
                        fetched_tag_names = [i[0] for i in await tag_names_availables.fetchall()]
                        matches = "\n".join(get_close_matches(tag_name,fetched_tag_names,n=3))
                        if len(matches) == 0:
                            return await ctx.send(f"I couldn't find anything close enough to '{tag_name}'. Try something else.")
                        else:
                            return await ctx.send(f"Tag '{tag_name}' not found. Maybe you meant :\n{matches}")
                            
    @tag.command()
    async def add(self,ctx,tag_name,*,description):
        guild_id = f"_{str(ctx.guild.id)}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = '{tag_name}';") as cursor:
                desc = await cursor.fetchone()
            if desc is not None:
                await ctx.send(f"Tag '{tag_name}' already exists in the database. Please pick another tag name !")
            else:
                await db.execute(f"INSERT INTO _{str(ctx.guild.id)} VALUES('{tag_name}','{description}')")
                await db.commit()
                await ctx.send(f"Successfully added '{tag_name}' tag.")
    
    @tag.command()
    async def edit(self,ctx,tag_name,*,description):
        guild_id = f"_{str(ctx.guild.id)}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = '{tag_name}';") as cursor:
                desc = await cursor.fetchone()
            if desc is None:
                await ctx.send(f"No tag named '{tag_name}', so you can't edit it. Please create it first.")
            else:
                await db.execute(f"UPDATE {guild_id} SET description = REPLACE(description,(SELECT description FROM {guild_id} WHERE tag_name = '{tag_name}'),'{description}')")
                await db.commit()
                await ctx.send(f"Succesfully edited '{tag_name}' tag.")

    @tag.command()
    async def remove(self,ctx,*,tag_name):
        guild_id = f"_{str(ctx.guild.id)}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = '{tag_name}';") as cursor:
                desc = await cursor.fetchone()
            if desc is None:
                await ctx.send(f"No tag named '{tag_name}', so you can't remove it.")
            else:
                await db.execute(f"DELETE FROM _{str(ctx.guild.id)} WHERE tag_name = '{tag_name}';")                     
                await db.commit()
                await ctx.send(f"Successfully removed '{tag_name}' tag.")

class ErrorHandler(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self,ctx, error):
        if isinstance(error, commands.CommandNotFound):
            cmd = ctx.invoked_with
            cmds = [cmd.name for cmd in bot.commands]
            matches = "\n".join(get_close_matches(cmd, cmds,n=3))
            if len(matches) > 0:
                return await ctx.send(f"Command \"{cmd}\" not found. Maybe you meant :\n{matches}")
            else:
                return await ctx.send(f'Command "{cmd}" not found, use the help command to know what commands are available')
        elif isinstance(error,commands.MissingPermissions):
            return await ctx.send(error)
        elif isinstance(error,commands.MissingRequiredArgument):
            return await ctx.send(error)
        elif isinstance(error,commands.NotOwner):
            await ctx.send("raté")
        else:
            raise error
        
@bot.command()
async def poll(ctx,*args):
    emote_alphabet = ["\U0001F1E6","\U0001F1E7","\U0001F1E8","\U0001F1E9","\U0001F1EA","\U0001F1EB","\U0001F1EC","\U0001F1ED","\U0001F1EE","\U0001F1EF","\U0001F1F0","\U0001F1F1","\U0001F1F2","\U0001F1F3","\U0001F1F4",
    "\U0001F1F5","\U0001F1F6","\U0001F1F7","\U0001F1F8","\U0001F1F9"]
    question = args[0]
    try:
        choices = "\n".join([f'{emote_alphabet[i]}  {args[i + 1]}' for i in range(len(args) - 1)])
        embed_poll = discord.Embed(title=question,description=choices,color=0xaaaaaa)
        embed_poll.set_footer(text=f"Requested by {ctx.author}.")
        message = await ctx.send(embed=embed_poll)
        for i in range(len(args) - 1):
            await message.add_reaction(emote_alphabet[i])
    except IndexError or Forbidden:
        await ctx.send("Discord doesn't allow me to react with more than 20 emojis. So you can't have more than 20 choices for your poll.")


@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

bot.add_cog(ChuckNorris(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(Music(bot))
bot.add_cog(Tags(bot))
bot.add_cog(ErrorHandler(bot))

bot.run(TOKEN)