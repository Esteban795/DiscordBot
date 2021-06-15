import functools
import typing
from dotenv import load_dotenv
import discord
import os
from discord.ext import commands
import requests
import asyncio
import youtube_dl
import aiosqlite
from difflib import get_close_matches
from datetime import datetime
import re
from PIL import Image,ImageDraw,ImageFont
from math import floor,ceil

time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])") #Detects patterns like "12d","10m"
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time

async def get_prefix(bot,message):
    """A callable that allows us to register custom prefixes"""
    if not message.guild:
        return "$"
    async with aiosqlite.connect("databases/main.db") as db:
        async with db.execute("SELECT custom_prefixes FROM prefixes WHERE guild_id = (?);",(message.guild.id,)) as cursor:
            result = await cursor.fetchone()
            if result is None:
                return "$"
            else:
                return result[0].split(" ") + ["$"]

load_dotenv()
bot = commands.Bot(command_prefix=get_prefix,description="A Chuck Norris dedicated discord bot !",intents=discord.Intents.all())

class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return  f'• `{self.clean_prefix}{command.qualified_name} {command.signature}`'

    async def send_bot_help(self, mapping):
        """Sends the bot help embed. This actually reveals every command registered in"""
        channel = self.get_destination() #Is ctx.channel
        embed = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="You asked for help, here I am.")
        for cog, commands in mapping.items(): #Iterate through every command cog and command registered (cog,[commands in the cog])
            filtered = await self.filter_commands(commands, sort=True) #Sort commands alphabetically
            command_signatures = [self.get_command_signature(c) for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)
        await channel.send(embed=embed)
    
    async def send_command_help(self, command):
        """Sends help for a specific command. This shows how you can use it. Example : $help kick will return $kick [member] (reason)"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="You asked for help, here I am.")
        emby.add_field(name="How to use this command : ",value=self.get_command_signature(command))
        if len(command.aliases):
            emby.add_field(name="Aliases you can use :",value=", ".join(command.aliases),inline=False)
        emby.add_field(name="Cooldown : ",value=command.cooldown_after_parsing,inline=False)
        await channel.send(embed=emby)
    
    async def send_group_help(self, group):
        """Sends help for a group of command. Specify a subcommand to get help from it too. Example : $help tags will show you $tag add, $tag remove etc"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="This command is actually a GROUP of command. Such awesome.")
        emby.add_field(name="Main command :",value=self.get_command_signature(group),inline=False)
        emby.add_field(name="Subcommands : ",value="\n".join([self.get_command_signature(i) for i in group.commands]))
        await channel.send(embed=emby)

    async def send_cog_help(self, cog):
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description=f"**{cog.qualified_name} category**")
        filtered = await self.filter_commands(cog.get_commands(),sort=True)
        command_signatures = [self.get_command_signature(c) for c in filtered]
        emby.add_field(name="Commands : ",value="\n".join(command_signatures))
        await channel.send(embed=emby)
        
bot.help_command= MyHelp() #A custom help command.
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
    async def chucknorris(self,ctx,*args):
        """Use this to get the best Chuck Norris jokes. Usage : $chucknorris (a category, available with cncategories)"""
        l = len(args)
        try:
            if l > 0:
                r = requests.get(f"https://api.chucknorris.io/jokes/random?category={args[0].lower()}") #Request to the API I'm using with a specific category
            else:
                r = requests.get("https://api.chucknorris.io/jokes/random") #Request to the API I'm using,random joke this time
            joke = r.json()["value"]
            categories = ",".join(r.json()["categories"]) if len(r.json()["categories"]) > 0 else "None"
            embedVar = discord.Embed(title=f"Categories : {categories}.",color=0xaaffaa)
            embedVar.add_field(name="This joke is provided to you by : Chuck Norris himself.",value=f"{joke}")
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        except KeyError: #Means the category doesn't exist on the API.
            embedVar = discord.Embed(title=f'There are no such categories as "{args[0]}".',color=0xff0000)
            embedVar.add_field(name="Don't try to fool me, I'll know it.",value="I'm also telling Chuck Norris about this. Watch your back.")
            embedVar.set_image(url="https://voi.img.pmdstatic.net/fit/http.3A.2F.2Fprd2-bone-image.2Es3-website-eu-west-1.2Eamazonaws.2Ecom.2Fvoi.2Fvar.2Fvoi.2Fstorage.2Fimages.2Fmedia.2Fmultiupload-du-25-juillet-2013.2Fchuck-norris-pl.2F8633422-1-fre-FR.2Fchuck-norris-pl.2Ejpg/460x258/quality/80/chuck-norris-vend-la-maison-qui-a-servi-de-decor-a-walker-texas-ranger.jpg")
            embedVar.set_footer(text="Pshhh. If you have no clue what categories are available, type '$ckcategories' !")
            await ctx.send(embed=embedVar)
    
    @commands.command(aliases=["cncat","cnc","cncategoires"])
    async def cncategories(self,ctx):
        """List the categories available from the API"""
        embedVar = discord.Embed(title="The categories of joke the bot can tell you.",color=0xaaffaa)
        r = requests.get("https://api.chucknorris.io/jokes/categories")
        embedVar.add_field(name="Pick your favourite ! ",value="\n".join(["• {}".format(i) for i in r.json()]))
        await ctx.send(embed=embedVar)

class Moderation(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    async def bot_check(self, ctx):
        """Checks if the message calls a command. If the channel is disabled or the member is banned from using commands, this will raise an error"""
        if ctx.command is not None:
            async with aiosqlite.connect("databases/main.db") as db:
                cursor = await db.execute("SELECT * FROM ignored_channels WHERE channel_id = ?",(ctx.channel.id,))
                res = await cursor.fetchone()
            if res:
                is_channel_ignored = True
            else:
                is_channel_ignored = False
            if is_channel_ignored:
                raise commands.DisabledCommand("You can't use commands in this channel.")
            return True
        elif not ctx.guild:
            raise commands.NoPrivateMessage("I can't be used in DM. Please, use this command in another channel.")

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        """Create the role muted as soon as the bot joins the guild, if no muted role exists. Disable send messages permissions and speak permissions for muted role in every channel"""
        existing_muted_role = discord.utils.get(guild.roles,name="muted") or discord.utils.get(guild.roles,name="Muted")
        if existing_muted_role:
            return
        mutedRole = await guild.create_role(name="Muted",permissions=discord.Permissions(send_messages=False,speak=False))
        for channel in guild.channels:
            await channel.set_permissions(mutedRole, send_messages = False, speak = False)
        async with aiosqlite.connect("databases/warns.db") as db:
            await db.execute(f"CREATE TABLE IF NOT EXISTS _{guild.id}(member_id INT,nb_warnings INT)")
            await db.execute(f"INSERT INTO _{guild.id} VALUES(0,5);")
            await db.commit()
        async with aiosqlite.connect("databases/main.db"):
            await db.execute(f"CREATE TABLE IF NOT EXISTS ignored_{guild.id}_members(member_id INT)")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild:discord.Guild):
        """When the bot leaves/gets kicked from a guild, no needs to store the warns since they are server dependent"""
        async with aiosqlite.connect("databases/warns.db") as db:
            await db.execute(f"DROP TABLE _{guild.id}")
            await db.commit()
    
    @commands.command(aliases=["addrole","roleadd"])
    @commands.has_permissions(manage_roles=True) #Check if the member of this guild has the permissions to manage roles.
    async def giverole(self,ctx,member:discord.Member,role:discord.Role):
        """Gives the member you mentionned a role"""
        await member.add_roles(role)
        embedVar = discord.Embed(description=f"{member} was granted the {role} role.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["rmvrole"])
    @commands.has_permissions(manage_roles = True)
    async def removerole(self,ctx,member : discord.Member, role:discord.Role):
        """Removes a role from the member you mentionned""" 
        await member.remove_roles(role)
        embedVar = discord.Embed(description=f"{member} lost the {role} role.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["gtfo"])
    @commands.has_permissions(kick_members = True)
    async def kick(self,ctx, member: discord.Member, *,reason="Not specified."):
        """Sends [member] a DM telling them they got kicked from the server you're in with the reason (if you told one)"""
        PMembed = discord.Embed(title="Uh oh. Looks like you did something quite bad !",color=0xff0000)
        PMembed.add_field(name=f"You were kicked from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
        await member.send(embed=PMembed)
        await member.kick(reason=reason)
        embedVar = discord.Embed(description=f"{member} was successfully kicked from the server.",color=0xaaffaa) #Confirms everything went okay
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_permissions()
    async def mute(self,ctx,member:discord.Member,time:TimeConverter=None):
        """Gives [member] the Muted role (they can't speak or write) for (time) if you specified one. After the mute duration is over, it automatically demutes them"""
        mutedRole = discord.utils.get(ctx.guild.roles,name="Muted") #Get the discord.Role instance
        if mutedRole:
            await member.add_roles(mutedRole)
            await ctx.send(("Muted {} for {}s" if time else "Muted {}").format(member, time))
            if time:
                await asyncio.sleep(time) #Sleeps without blocking the bot code.
                await member.remove_roles(mutedRole)
    
    @commands.command(aliases=["demute"])
    @commands.has_permissions()
    async def unmute(self,ctx,user:discord.Member):
        """Removes the Muted role from the member. They now have the permission to speak/write"""
        mutedRole = discord.utils.get(ctx.guild.roles,name="Muted") 
        await user.remove_roles(mutedRole)

    @commands.command(aliases=["banl","bl"])
    @commands.has_permissions(administrator = True)
    async def banlist(self,ctx):
        """Sends the current banlist from this server""" 
        bans = await ctx.guild.bans()
        if len(bans) == 0: #Are there members banned from this server ?
            embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        else:
            embedVar = discord.Embed(title="Here are all the people banned on this server : ",color=0xaaffaa)
            pretty_list = ["• {}#{} for : {} ".format(entry.user.name,entry.user.discriminator,entry[0]) for entry in bans]
            embedVar.add_field(name=f"There are {len(pretty_list)} of them ! ",value="\n".join(pretty_list))
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(ban_members = True)
    async def ban(self,ctx,member:discord.Member,*,reason="Not specified."):
        """Bans a member from the server. This is a group, which means you CAN use subcommands for more specific ban options. 
        The current command just bans a member from the server, and sends them a DM with the reason they got banned"""
        if ctx.invoked_subcommand is None: #Check if a subcommand is passed in.
            embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
            embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await member.send(embed=embedVar)
            await member.ban(reason=reason)

    @ban.command()
    async def match(ctx,r,*,words):
        """Bans every member that said [words] in the last 100 messages of this channel. Reason must be quoted if it isn't a single word"""
        banned_words = words.split(" ")
        last_100_messages = await ctx.channel.history(limit=123).flatten()
        count = 0
        for message in last_100_messages:
            if message.author == ctx.author or message.author.bot:
                continue
            for word in banned_words:
                if word in message.content:
                    embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
                    embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {r}")
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await message.author.send(embed=embedVar)
                    await message.author.ban(reason=reason)
                    count += 1
                    break
        if count:
            await ctx.send((f'Done ! I banned {count} people.' if count > 1 else "Done ! I banned one person."))
        else:
            await ctx.send("No one said those awful words.")

    @ban.group(invoke_without_command=True)
    async def time(self,ctx,member:discord.Member,time:TimeConverter,*,reason="Not specified."):
        if ctx.invoked_subcommand is None:
            embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
            embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await member.send(embed=embedVar)
            await member.ban(reason=reason)
            await asyncio.sleep(time)
            await member.unban(reason="Ban duration ended.")
    
    @time.command()
    async def match(ctx,time:TimeConverter,reason,*,words):
        """Bans every member that said [words] in the last 100 messages of this channel. Reason must be quoted if it isn't a single word"""
        banned_words = words.split(" ")
        last_100_messages = await ctx.channel.history(limit=123).flatten()
        banned_people = []
        for message in last_100_messages:
            if message.author == ctx.author or message.author.bot:
                continue
            for word in banned_words:
                if word in message.content:
                    embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
                    embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await message.author.send(embed=embedVar)
                    await message.author.ban(reason=reason)
                    banned_people.append(message.author)
                    break
        n = len(banned_people)
        if n:
            await ctx.send((f'Done ! I banned {n} people. They will be unbanned in {time} seconds.' if n > 1 else f"Done ! I banned one person. They will be unbanned in {time} seconds."))
        else:
            await ctx.send("No one said those awful words.")
        await asyncio.sleep(time)
        for i in banned_people:
            await i.unban()


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

    @commands.group(invoke_without_command=True)
    async def warn(self,ctx,member:discord.Member,*,reason=None):
        if ctx.invoked_subcommand is None:
            table_name = f"_{ctx.guild.id}"
            async with aiosqlite.connect("databases/warns.db") as db:
                cursor =  await db.execute(f"SELECT nb_warnings FROM {table_name}  WHERE member_id = ?",(member.id,))
                result = await cursor.fetchone()
                number_of_warns_allowed = await db.execute(f"SELECT nb_warnings FROM {table_name} WHERE member_id = 0;")
                res = await number_of_warns_allowed.fetchone()
                if result:
                    new_warns_number = result[0] + 1
                    if new_warns_number >= int(res[0]):
                        await db.execute(f"DELETE FROM {table_name} WHERE member_id = ?;",(member.id,))
                        await db.commit()
                        await member.kick(reason=reason)
                        await ctx.send(f"{member} was kicked due to too many warns !")

                    else:
                        await db.execute(f"UPDATE {table_name} SET nb_warnings = ? WHERE member_id = ?",(new_warns_number,member.id))
                        await db.commit()
                else:
                    await db.execute(f"INSERT INTO {table_name} VALUES(?,1);",(member.id,))
                    await db.commit()
    
    @warn.command()
    async def changenumber(self,ctx,amount:int):
        table_name =  f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/warns.db") as db:
            cursor = await db.execute(f"SELECT nb_warnings FROM {table_name} WHERE member_id = 0;")
            res = await cursor.fetchone()
            try:
                await ctx.send(f"Currently, {res[0]} warning(s) gets you auto-kicked. Are you sure you want to change that to {amount} ?")
                confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
            except asyncio.TimeoutError:
                await ctx.send("You didn't answer fast enough. Aborting mission !")
            else:
                if confirm.content.lower() == "yes":
                    await db.execute(f"UPDATE {table_name} SET nb_warnings = ? WHERE member_id = 0;",(amount,))
                    await db.commit()

    @commands.command(aliases=["sb"])
    async def softban(self,ctx,member:discord.Member,*,reason):
        await member.ban(reason=reason)
        await member.unban(reason="Softban.")
        await ctx.send(f"{member} was softbanned.")

    @commands.group()
    async def ignore(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use the 'member' or 'channel' subcommand to specify who shouldn't be allowed to use a command, or where people won't be allowed to use those beautiful commands !")
    
    @ignore.command()
    async def channel(self,ctx,channel:discord.TextChannel):
        async with aiosqlite.connect("databases/main.db") as db:
            cursor = await db.execute("SELECT channel_id FROM ignored_channels WHERE channel_id = ?",(channel.id,))
            result = await cursor.fetchone()
            if result:
                await ctx.send("This channel is already ignored. Type 'yes' if you want people to be able to use commands there !")
                try:
                    answer = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
                except asyncio.TimeoutError:
                    await ctx.send("You didn't answer fast enough. Aborting the process !")
                else:
                    await db.execute("DELETE FROM ignored_channels WHERE channel_id = ?",(channel.id,))
                    await db.commit()
                    await ctx.send(f"{channel.mention} now has enabled commands !")
            else:
                await db.execute("INSERT INTO ignored_channels VALUES(?);",(channel.id,))
                await db.commit()
                await ctx.send(f"{channel.mention} now has disabled commands !")


    @commands.group(invoke_without_command=True,name="purge")
    async def purge(self,ctx,Amount:int=2): #Delete "Amount" messages from the current channel. $purge [int]
        await ctx.message.delete()
        if ctx.invoked_subcommand is None:
            await ctx.channel.purge(limit=int(Amount))
    
    @purge.command()
    async def commands(self,ctx,amount:int=2):
        guild_prefix = tuple(await get_prefix(self.bot,ctx.message))
        await ctx.channel.purge(limit=amount,check=lambda m:m.author.bot or m.content.startswith(guild_prefix))
 
    @purge.command()
    async def bots(selt,ctx,amount:int=2):
        await ctx.channel.purge(limit=amount,check=lambda m:m.author.bot)
        await ctx.message.delete()
    
    @purge.command()
    async def humans(self,ctx,amount:int=2):
        guild_prefix = tuple(await get_prefix(self.bot,ctx.message))
        await ctx.channel.purge(limit=amount,check=lambda m:not (m.author.bot or m.content.startswith(guild_prefix)))
    
    @purge.command()
    async def member(self,ctx,amount:int=2,member:discord.Member=None):
        member = member or ctx.author
        await ctx.channel.purge(limit=amount,check=lambda m:m.author == member)
        await ctx.message.delete()
    
    @purge.command()
    async def match(self,ctx,amount:int=2,*,content):
        await ctx.channel.purge(limit=amount,check=lambda m:content in m.content)
    
    @purge.command(name="not")
    async def _not(self,ctx,amount:int=2,*,content):
        await ctx.channel.purge(limit=amount,check=lambda m:not (content in m.content))
        await ctx.message.delete()
    
    @purge.command()
    async def startswith(self,ctx,amount:int=2,*,content):
        await ctx.channel.purge(limit=amount,check=lambda m:m.content.startswith(content))
        await ctx.message.delete()
    
    @purge.command()
    async def endswith(self,ctx,amount:int=2,*,content):
        await ctx.channel.purge(limit=amount,check=lambda m:m.content.endswith(content))
        
    @purge.command()
    async def embeds(self,ctx,amount:int=2):
        await ctx.channel.purge(limit=amount,check=lambda m:len(m.embeds))
        await ctx.message.delete()

    @purge.command()
    async def images(self,ctx,amount:int=2):
        await ctx.channel.purge(limit=amount,check=lambda m:len(m.attachments) or m.content.startswith(("https://cdn.discordapp.com/attachments/","https://tenor.com/view/")))
        await ctx.message.delete()


            
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
    async def on_member_remove(self,member):
        guild_id = f"_{member.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"UPDATE {guild_id} SET creator_id = 'Null' WHERE creator_id = ?",(member.id,))
            await db.commit()

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"CREATE TABLE IF NOT EXISTS _{guild.id}(tag_name TEXT,description TEXT,creator_id INT);")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"DROP TABLE _{guild.id};")
            await db.commit()
    
    @commands.group(invoke_without_command=True)
    async def tag(self,ctx,*,tag_name):
        guild_id = f"_{ctx.guild.id}"
        if ctx.invoked_subcommand is None:
            async with aiosqlite.connect("databases/tags.db") as db:
                async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = ?",(tag_name,)) as cursor:
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
    async def all(self,ctx):
        guild_id = f"_{ctx.guild.id}"
        l = []
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT * FROM {guild_id}") as cursor:
                async for row in cursor:
                    l.append(f"{row[0]} : {row[1]}")
        if len(l) == 0:
            return await ctx.send("No tags registered on this server.")
        return await ctx.send("\n".join(l))
    
    @tag.command()
    async def createdby(self,ctx,member:typing.Union[discord.Member,int]=None):
        member = member or ctx.author
        guild_id = f"_{ctx.guild.id}"
        if member is int:
            member_id = member
        else:
            member_id = member.id
        l = []
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT tag_name,description FROM {guild_id} WHERE creator_id = ?",(member_id,)) as cursor:
                async for row in cursor:
                    l.append(f"{row[0]} : {row[1]}")
        if len(l) == 0:
            return await ctx.send("This member doesn't own any tags !")
        return await ctx.send("\n".join(l))
        
    @tag.command()
    async def add(self,ctx,tag_name,*,description):
        print(f"Tag name : {tag_name}")
        print(f"Description : {description}")
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = ?;",(tag_name,)) as cursor:
                desc = await cursor.fetchone()
            if desc is not None:
                await ctx.send(f"Tag '{tag_name}' already exists in the database. Please pick another tag name !")
            else:
                await db.execute(f"INSERT INTO {guild_id} VALUES(?,?,?)",(tag_name,description,ctx.author.id))
                await db.commit()
                await ctx.send(f"Successfully added '{tag_name}' tag.")
    
    @tag.command()
    async def edit(self,ctx,tag_name,*,description):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description,creator_id FROM {guild_id} WHERE tag_name = ?;",(tag_name,)) as cursor:
                desc = await cursor.fetchone()
            if desc is None:
                return await ctx.send(f"No tag named '{tag_name}', so you can't edit it. Please create it first.")
            elif desc[1] != ctx.author.id and desc[1] != "Null":
                return await ctx.send("You must own the tag to edit it. Or the person who created the tag left the server. Then everyone is free to edit or remove it.")
            else:
                await db.execute(f"UPDATE {guild_id} SET description = ? WHERE tag_name = ?",(description,tag_name))
                await db.commit()
                await ctx.send(f"Succesfully edited '{tag_name}' tag.")

    @tag.command()
    async def remove(self,ctx,*,tag_name):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description,creator_id FROM {guild_id} WHERE tag_name = ?;",(tag_name,)) as cursor:
                desc = await cursor.fetchone()
            if desc is None:
                await ctx.send(f"No tag named '{tag_name}', so you can't remove it.")
            elif desc[1] != ctx.author.id and desc[1] != "Null":
                return await ctx.send("You must own the tag to remove it.")
            else:
                await db.execute(f"DELETE FROM {guild_id} WHERE tag_name = ?;",(tag_name,))                     
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
            await ctx.send("You must be the owner of this bot to perform this command. Please contact Esteban#7985 for more informations.")
        elif isinstance(error,commands.BadArgument):
            await ctx.send(error)
        elif isinstance(error,commands.DisabledCommand):
            await ctx.send(error)
        elif isinstance(error,commands.NoPrivateMessage):
            await ctx.send(error)
        else:
            raise error

class Poll(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.emote_alphabet = ["\U0001F1E6","\U0001F1E7","\U0001F1E8","\U0001F1E9","\U0001F1EA","\U0001F1EB","\U0001F1EC","\U0001F1ED","\U0001F1EE","\U0001F1EF","\U0001F1F0","\U0001F1F1","\U0001F1F2","\U0001F1F3","\U0001F1F4",
    "\U0001F1F5","\U0001F1F6","\U0001F1F7","\U0001F1F8","\U0001F1F9"]

    @commands.command(aliases=["study"],help="test")
    async def poll(self,ctx,*args):
        if len(args) > 1:
            question = args[0].capitalize()
            try:
                choices = "\n".join([f'{self.emote_alphabet[i]}  {args[i + 1].capitalize()}' for i in range(len(args) - 1)])
                embed_poll = discord.Embed(title=question,description=choices,color=0xaaaaaa)
                embed_poll.set_footer(text=f"Requested by {ctx.author}.")
                message = await ctx.send(embed=embed_poll)
                for i in range(len(args) - 1):
                    await message.add_reaction(self.emote_alphabet[i])
            except IndexError:
                await ctx.send("Discord doesn't allow me to react with more than 20 emojis. So you can't have more than 20 choices for your poll.")
        else:
            return await ctx.send("I need at least the topic of the poll and an option. Please provide them both.")
    
    @commands.command()
    async def timedpoll(self,ctx,time:TimeConverter,question,*args):
        if len(args) > 0:
            try:
                choices = "\n".join([f'{self.emote_alphabet[i]}  {args[i].capitalize()}' for i in range(len(args))])
                embed_poll = discord.Embed(title=question,description=choices,color=0xaaaaaa)
                embed_poll.add_field(name="Expires on :",value="test")
                embed_poll.set_footer(text=f"Requested by {ctx.author}.")
                message = await ctx.send(embed=embed_poll)
                for i in range(len(args)):
                    await message.add_reaction(self.emote_alphabet[i])
                await asyncio.sleep(time)
                cached_message = discord.utils.get(bot.cached_messages, id=message.id)
                reactions_count = sorted([(cached_message.reactions[i].count,i) for i in range(len(args))],key=lambda x:x[0],reverse=True)[0]
                timed_embed_poll = discord.Embed(title=f"Poll '{question.capitalize()}' just ended !",color=0xaaffaa,timestamp=datetime.utcnow(),description=f"Proposition '{args[reactions_count[1]].capitalize()}' won with {reactions_count[0] - 1} votes !")
                await ctx.send(embed=timed_embed_poll)
            except IndexError as e:
                await ctx.send("Discord doesn't allow me to react with more than 20 emojis. So you can't have more than 20 choices for your poll.")
        else:
            await ctx.send("I need at least the topic of the poll and an option. Please provide them both.")


class Logs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    async def get_logs_channels(self,guild_id):
        async with aiosqlite.connect("databases/main.db") as db:
            cursor = await db.execute("SELECT channel_id FROM logs_channels WHERE guild_id = (?);",(guild_id,))
            result = await cursor.fetchone()
        if result:
            return result[0]
        return None

    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("DELETE FROM logs_channels WHERE guild_id = (?);",(guild.id,))
            await db.commit()

    @commands.group(invoke_without_command=True,aliases=["log"])
    async def logs(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Subcommand required.")
    
    @logs.group()
    async def logchannel(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Either add, edit or remove a log channel.")
    
    @logchannel.command()
    async def add(self,ctx,text_channel:discord.TextChannel):
        await text_channel.send(f"{ctx.author} picked this channel to be the log channel. I will send everything I can track here (kick, ban, messages deleted,reactions added etc..).")
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("INSERT INTO logs_channels VALUES(?,?);",(ctx.guild.id,text_channel.id))
            await db.commit()
    
    @logchannel.command()
    async def remove(self,ctx):
        await ctx.send(f"{ctx.author} decided to disable the logs in this channel. You can always re-add it back later !")
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("DELETE FROM logs_channels WHERE guild_id = (?);",(ctx.guild.id,))
            await db.commit()
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.author.bot and not message.is_system() and message.guild:
            channel_id = await self.get_logs_channels(message.guild.id)
            if channel_id:
                channel = message.guild.get_channel(channel_id)
                logEmbed = discord.Embed(title="New message !",color=0xaaffaa,timestamp=datetime.utcnow())
                logEmbed.add_field(name="Channel :",value=message.channel.mention)
                logEmbed.add_field(name="Message : ",value=f"[{message.content}]({message.jump_url})")
                logEmbed.set_author(name=message.author,icon_url=message.author.avatar_url)
                await channel.send(embed=logEmbed)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        if not payload.member.bot:
            channel_id = await self.get_logs_channels(payload.guild_id)
            if channel_id:
                channel = payload.member.guild.get_channel(channel_id)
                reaction_channel = payload.member.guild.get_channel(payload.channel_id)
                msg = await reaction_channel.fetch_message(payload.message_id)
                reaction_embed = discord.Embed(title="Reaction added.",color=0xaaffaa,timestamp=datetime.utcnow())
                reaction_embed.add_field(name="Member who added the reaction :",value=payload.member)
                reaction_embed.add_field(name="Reaction added :",value=payload.emoji.name)
                reaction_embed.add_field(name="Original message :",value=f"[{msg.content}]({msg.jump_url})")
                await channel.send(embed=reaction_embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self,payload):
        user = self.bot.get_user(payload.user_id)
        if not user.bot:
            channel_id = await self.get_logs_channels(payload.guild_id)
            if channel_id:
                guild = self.bot.get_guild(payload.guild_id)
                channel = guild.get_channel(channel_id)
                reaction_channel = guild.get_channel(payload.channel_id)
                msg = await reaction_channel.fetch_message(payload.message_id)
                reaction_embed = discord.Embed(title="Reaction removed.",color=0xaaffaa,timestamp=datetime.utcnow())
                reaction_embed.add_field(name="Member who removed the reaction :",value=user)
                reaction_embed.add_field(name="Reaction removed :",value=payload.emoji.name)
                reaction_embed.add_field(name="Original message :",value=f"[{msg.content}]({msg.jump_url})")
                reaction_embed.set_author(name=user,icon_url=user.avatar_url)
                await channel.send(embed=reaction_embed)
    
    @commands.Cog.listener()
    async def on_raw_message_edit(self,payload):
        guild_id = int(payload.data["guild_id"])
        log_channel_id = await self.get_logs_channels(guild_id)
        if log_channel_id:
            user = self.bot.get_user(int(payload.data["author"]["id"]))
            if not user.bot:
                if payload.cached_message:
                    log_channel = payload.cached_message.guild.get_channel(log_channel_id)
                    if payload.data["pinned"] == payload.cached_message.pinned:
                        edit_embed = discord.Embed(title="Message edited.",color=0xaaffaa,timestamp=datetime.utcnow())
                        edit_embed.add_field(name="Old message :",value=payload.cached_message.content)
                        edit_embed.add_field(name="Message originally sent at :",value=payload.data["timestamp"],inline=True)
                        edit_embed.add_field(name="New message",value=f"[{payload.data['content']}]({payload.cached_message.jump_url})")
                        edit_embed.set_author(name=user,icon_url=user.avatar_url)
                    else:
                        edit_embed = discord.Embed(title="Message pinned/unpinned.",color=0xaaffaa,timestamp=datetime.utcnow())
                        edit_embed.add_field(name="Channel :",value=payload.cached_message.channel)
                        edit_embed.add_field(name="Message :",value=f"[{payload.cached_message.content}]({payload.cached_message.jump_url})")
                        edit_embed.set_author(name=user,icon_url=user.avatar_url)
                        
                else:
                    guild = self.bot.get_guild(guild_id)
                    log_channel = guild.get_channel(log_channel_id)
                    original_channel = guild.get_channel(payload.channel_id)
                    msg = await original_channel.fetch_message(payload.message_id)
                    edit_embed = discord.Embed(title="Message edited.",color=0xaaffaa,timestamp=datetime.utcnow())
                    edit_embed.add_field(name="Old message :",value="The message was sent when I was offline or it's too old.")
                    edit_embed.add_field(name="New message",value=f"[{payload.data['content']}]({msg.jump_url})")
                    edit_embed.set_author(name=user,icon_url=user.avatar_url)
                return await log_channel.send(embed=edit_embed)
                    
    @commands.Cog.listener()
    async def on_raw_message_delete(self,payload):
        log_channel_id = await self.get_logs_channels(payload.guild_id)
        if log_channel_id:
            if payload.cached_message:
                log_channel = payload.cached_message.author.guild.get_channel(log_channel_id)
                delete_message_embed = discord.Embed(title="Message deleted.",color=0xaaffaa,timestamp=datetime.utcnow())
                delete_message_embed.add_field(name="Channel : ",value=payload.cached_message.channel)
                if len(payload.cached_message.embeds):
                    delete_message_embed.add_field(name="Message content :",value="This was an embed. I can't tell you what was in !")
                else:
                    delete_message_embed.add_field(name="Message content :",value=payload.cached_message.content)
                    delete_message_embed.set_author(name=payload.cached_message.author,icon_url=payload.cached_message.author.avatar_url)
            else:
                guild = self.bot.get_guild(payload.guild_id)
                log_channel = guild.get_channel(log_channel_id)
                original_channel = guild.get_channel(payload.channel_id)
                delete_message_embed = discord.Embed(title="Message deleted.",color=0xaaffaa,timestamp=datetime.utcnow())
                delete_message_embed.add_field(name="Message content :",value="The message was sent when I was offline or is too old. No more informations about it.")
                delete_message_embed.add_field(name="Channel : ",value=original_channel)
            return await log_channel.send(embed=delete_message_embed)
        

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self,payload):
        log_channel_id = await self.get_logs_channels(payload.guild_id)
        if log_channel_id:
            guild = payload.cached_messages[0].guild
            log_channel = guild.get_channel(log_channel_id)
            original_channel = guild.get_channel(payload.channel_id)
            bulk_delete_embed = discord.Embed(title=f"{len(payload.message_ids) - 1} messages deleted in {original_channel} channel.")
            bulk_delete_embed.set_author(name=payload.cached_messages[0].author,icon_url=payload.cached_messages[0].author.avatar_url)
            return await log_channel.send(embed=bulk_delete_embed)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self,payload):
        log_channel_id = await self.get_logs_channels(payload.guild_id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            original_channel = bot.get_channel(payload.channel_id)
            message = await original_channel.fetch_message(payload.message_id)
            reaction_clear_embed = discord.Embed(title="Reactions cleared.",color=0xaaffaa,timestamp=datetime.utcnow())
            reaction_clear_embed.add_field(name="Channel : ",value=original_channel)
            reaction_clear_embed.add_field(name="Message : ",value=f"[{message.content}]({message.jump_url})")
            await log_channel.send(embed=reaction_clear_embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self,channel):
        log_channel_id = await self.get_logs_channels(channel.guild.id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            channel_deleted_embed = discord.Embed(title=f"{channel.type} channel deleted.".capitalize(),color=0xaaffaa,timestamp=datetime.utcnow())
            channel_deleted_embed.add_field(name="Category :",value=channel.category)
            channel_deleted_embed.add_field(name="Name  :",value=channel.name,inline=True)
            channel_deleted_embed.add_field(name="Created at  :",value=str(channel.created_at)[:-7],inline=True)
            if str(channel.type) == "text":
                channel_deleted_embed.add_field(name="Topic :",value=f"{channel.topic}.".capitalize())
                channel_deleted_embed.add_field(name="Slowmode delay :",value=channel.slowmode_delay)
            elif str(channel.type) == "voice":
                channel_deleted_embed.add_field(name="User limit : ",value=channel.user_limit)
            await log_channel.send(embed=channel_deleted_embed)


    @commands.Cog.listener()
    async def on_guild_channel_create(self,channel):
        log_channel_id = await self.get_logs_channels(channel.guild.id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            channel_created_embed = discord.Embed(title=f"{channel.type} channel created.".capitalize(),color=0xaaffaa,timestamp=datetime.utcnow())
            channel_created_embed.add_field(name="Category :",value=channel.category)
            channel_created_embed.add_field(name="Name  :",value=channel.name,inline=True)
            if str(channel.type) == "text":
                channel_created_embed.add_field(name="Topic :",value=f"{channel.topic}.".capitalize())
                channel_created_embed.add_field(name="Slowmode delay :",value=channel.slowmode_delay)
            elif str(channel.type) == "voice":
                channel_created_embed.add_field(name="User limit : ",value=channel.user_limit)
            await log_channel.send(embed=channel_created_embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self,before,after):
        log_channel_id = await self.get_logs_channels(before.guild.id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            channel_updated_before_embed = discord.Embed(title=f"{before.type} channel updated. (Before update)".capitalize(),color=0xaaffaa,timestamp=datetime.utcnow())
            channel_updated_before_embed.add_field(name="Category :",value=before.category)
            channel_updated_before_embed.add_field(name="Name  :",value=before.name,inline=True)
            channel_updated_after_embed = discord.Embed(title=f"{after.type} channel updated. (After update)".capitalize(),color=0xaaffaa,timestamp=datetime.utcnow())
            channel_updated_after_embed.add_field(name="Category :",value=before.category)
            channel_updated_after_embed.add_field(name="Name  :",value=after.name,inline=True)
            if str(before.type) == "text":
                channel_updated_before_embed.add_field(name="Topic :",value=f"{before.topic}.".capitalize())
                channel_updated_before_embed.add_field(name="Slowmode delay :",value=before.slowmode_delay)
                channel_updated_after_embed.add_field(name="Topic :",value=f"{after.topic}.".capitalize())
                channel_updated_after_embed.add_field(name="Slowmode delay :",value=after.slowmode_delay)
            elif str(before.type) == "voice":
                channel_updated_before_embed.add_field(name="User limit : ",value=before.user_limit)
                channel_updated_after_embed.add_field(name="User limit : ",value=after.user_limit)
            await log_channel.send(embed=channel_updated_before_embed)
            await log_channel.send(embed=channel_updated_after_embed)
    
    @commands.Cog.listener()
    async def on_member_join(self,member):
        log_channel_id = await self.get_logs_channels(member.guild.id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            member_join_embed = discord.Embed(title="A member just joined the guild.",color=0xaaffaa,timestamp=datetime.utcnow())
            member_join_embed.add_field(name="Created account at :",value=member.created_at)
            member_join_embed.set_author(name=member,url=member.dm_channel,icon_url=member.avatar_url)
            member_join_embed.add_field(name="Public flags :",value=member.public_flags)
            await log_channel.send(embed=member_join_embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self,member):
        log_channel_id = await self.get_logs_channels(member.guild.id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            member_join_embed = discord.Embed(title="A member just left the guild.",color=0xaaffaa,timestamp=datetime.utcnow())
            member_join_embed.add_field(name="Joined at :",value=member.joined_at)
            member_join_embed.set_author(name=member,url=member.dm_channel,icon_url=member.avatar_url)
            member_join_embed.add_field(name="Public flags :",value=member.public_flags)
            await log_channel.send(embed=member_join_embed)
    
    @commands.Cog.listener()
    async def on_member_update(self,before,after):
        if before.activity != after.activity or before.status != after.status:
            return
        log_channel_id = await self.get_logs_channels(before.guild.id)
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            member_updated_embed = discord.Embed(title=f"{before} updated.",color=0xaaffaa,timestamp=datetime.utcnow())
            if not before.display_name == after.display_name:
                member_updated_embed.add_field(name="Old nickname : ",value=before.display_name)
                member_updated_embed.add_field(name="New nickname : ",value=after.display_name)
            if not before.roles == after.roles:
                member_updated_embed.add_field(name="Old roles : ",value=" ".join([i.name for i in before.roles]))
                member_updated_embed.add_field(name="New roles : ",value=" ".join([i.name for i in after.roles]))
            await log_channel.send(embed=member_updated_embed)

class CustomPrefixes(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("DELETE FROM prefixes WHERE guild_id = (?);",(guild.id,))
            await db.commit()
    
    @commands.group()
    async def prefix(self,ctx):
        if ctx.invoked_subcommand is None:
            async with aiosqlite.connect("databases/main.db") as db:
                cursor = await db.execute("SELECT custom_prefixes FROM prefixes WHERE guild_id = ?",(ctx.guild.id,))
                result = await cursor.fetchone()
        return await ctx.send(f"Custom prefixes for this discord server : {' '.join([i for i in result])}")

    @prefix.command()
    async def add(self,ctx,*,custom_prefixes):
        async with aiosqlite.connect("databases/main.db") as db: 
            check_for_existing_prefixes = await db.execute("SELECT custom_prefixes FROM prefixes WHERE guild_id = (?)",(ctx.guild.id,))
            existing_custom_prefixes = await check_for_existing_prefixes.fetchone()
            if existing_custom_prefixes:
                new_custom_prefixes = f"{custom_prefixes} {existing_custom_prefixes[0]}"
                await db.execute("UPDATE prefixes SET custom_prefixes = (?) WHERE guild_id = (?);",(new_custom_prefixes,ctx.guild.id))
                await db.commit()
            else:
                new_custom_prefixes = custom_prefixes
                await db.execute("INSERT INTO prefixes VALUES(?,?);",(ctx.guild.id,custom_prefixes))
                await db.commit()
        await ctx.send(f"New custom prefixes : {new_custom_prefixes}")

    @prefix.command()
    async def remove(self,ctx):
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("DELETE FROM prefixes WHERE guild_id = (?);",(ctx.guild.id,))
            await db.commit()
        await ctx.send("Custom prefixes were removed. You now have to use my default prefix, which is '$'.")
    
    @prefix.command()
    async def edit(self,ctx,*,custom_prefixes):
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("UPDATE prefixes SET custom_prefixes = (?) WHERE guild_id = (?);",(custom_prefixes,ctx.guild.id))
            await db.commit()
        await ctx.send(f"Custom prefixes edited. You can now use : {custom_prefixes} and of course '$' !")
        
class CustomOnMessage(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if message.author == self.bot.user or not message.guild:
            return
        table = f"_{message.guild.id}"
        async with aiosqlite.connect("databases/custom_on_message.db") as db:
            cursor = await db.execute(f"SELECT description FROM {table} WHERE message_name = ?",(message.content,))
            result = await cursor.fetchone()
            if result:
                await message.channel.send(result[0])

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        async with aiosqlite.connect("databases/custom_on_message.db") as db:
            await db.execute(f"CREATE TABLE _{guild.id}(message_name TEXT,description TEXT);")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/custom_on_message.db") as db:
            await db.execute(f"DROP TABLE _{guild.id};")
            await db.commit()  
    
    @commands.group(aliases=["COM","com"])
    async def CustomOnMessage(self,ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send("Subcommand required.")
    
    @CustomOnMessage.command()
    async def add(self,ctx,trigger,*,message):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/custom_on_message.db") as db:
            cursor = await db.execute(f"SELECT message_name,description FROM {guild_id} WHERE message_name = ?",(trigger,))
            check_result = await cursor.fetchone()
            if check_result:
                return await ctx.send(f"'{trigger}' already calls an other message ! Pick another name (this is case sensitive).")
            await db.execute(f"INSERT INTO {guild_id} VALUES(?,?)",(trigger,message))
            await db.commit()
        await ctx.send(f"Got it ! If anyone says '{trigger}', I will answer '{message}'.")
    
    @CustomOnMessage.command()
    async def remove(self,ctx,trigger):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/custom_on_message.db") as db:
            cursor = await db.execute(f"SELECT message_name,description FROM {guild_id} WHERE message_name = ?",(trigger,))
            check_result = await cursor.fetchone()
            if not check_result:
                return await ctx.send("Uhm. Actually, this message doesn't call any message from me. Can't remove something that doesn't exist, right ?")
            await db.execute(f"DELETE FROM {guild_id} WHERE message_name = ?",(trigger,))
            await db.commit()
        await ctx.send(f"Got it. I won't answer to '{trigger}' anymore !")

    @CustomOnMessage.command()
    async def edit(self,ctx,trigger,*,message):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/custom_on_message.db") as db:
            cursor = await db.execute(f"SELECT message_name,description FROM {guild_id} WHERE message_name = ?",(trigger,))
            check_result = await cursor.fetchone()
            if not check_result:
                return await ctx.send("Uhm. Actually, this message doesn't call any message from me. Can't edit something that doesn't exist, right ?")
            await db.execute(f"UPDATE {guild_id} SET description = ? WHERE message_name = ?",(message,trigger))
            await db.commit()
        await ctx.send(f"Just edited what '{trigger}' calls. Now calls '{message}' ! ")

#Suite ag : 40*1.1**n - 30
class XPSystem(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1.0, 10.0, commands.BucketType.member)
        self.suite1 = "40*1.1**"
        self.suite2 = "-30"
        self.u0 = 10

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage("These cannot be used in private messages.")
    def ratelimit_check(self, message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        async with aiosqlite.connect("databases/xp.db") as db:
            await db.execute(f"CREATE TABLE _{guild.id}(member_id INT,current_xp INT,next_level_xp INT,current_level INT);")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/xp.db") as db:
            await db.execute(f"DROP TABLE _{guild.id};")
            await db.commit() 

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        table_name = f"_{member.guild.id}"
        async with aiosqlite.connect("databases/xp.db") as db:
            await db.execute(f"DELETE FROM {table_name} WHERE member_id = ?",(member.id,))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self,message):
        retry_after = self.ratelimit_check(message)
        guild_prefix = tuple(await get_prefix(self.bot,message))
        if message.author.bot or message.content.startswith(guild_prefix) or not message.guild:
            return
        if retry_after is None:
            xp_won = 1 + ceil(min(len(message.content)//10,1) * 8)
            table_name = f"_{message.guild.id}"
            async with aiosqlite.connect("databases/xp.db") as db:
                cursor = await db.execute(f"SELECT current_xp,next_level_xp,current_level FROM {table_name} WHERE member_id = ?",(message.author.id,))
                result = await cursor.fetchone()
                if result:
                    current_xp = result[0] + xp_won
                    next_level_xp = result[1]
                    current_level = result[2]
                    if current_xp >= next_level_xp:
                        while current_xp >= next_level_xp:
                            current_xp -= next_level_xp
                            next_level_xp = floor(eval("".join([self.suite1,str(current_level + 1),self.suite2])))
                            current_level += 1
                        await db.execute(f"UPDATE {table_name} SET current_xp = ?,next_level_xp = ?,current_level = ? WHERE member_id = ?",(current_xp,next_level_xp,current_level,message.author.id))
                        await db.commit()
                        await message.channel.send(f"{message.author.mention} vient de passer au niveau {current_level} ! ")
                    else:
                        await db.execute(f"UPDATE {table_name} SET current_xp = ? WHERE member_id = ?",(current_xp,message.author.id))
                        await db.commit()
                else:
                    await db.execute(f"INSERT INTO {table_name} VALUES(?,?,?,0);",(message.author.id,xp_won,self.u0))
                    await db.commit()


    def xpcard(self,member_id,member_name,rank,level,xp,xp_level_suivant):
        FNT_30 = ImageFont.truetype("fonts/universcondensed.ttf", 30)
        FNT_25 = ImageFont.truetype("fonts/universcondensed.ttf", 25)
        FNT_20 = ImageFont.truetype("fonts/universcondensed.ttf", 20)
        avatar = Image.open(f'avatars/{member_id}_avatar.png').resize((125,125))

        background_to_crop = Image.new("L", avatar.size,color=0)
        im_rgba = avatar.copy()
        draw = ImageDraw.Draw(background_to_crop)
        draw.ellipse((0,0,125,125), fill=255)
        im_rgba.putalpha(background_to_crop)
        im_rgba_crop = im_rgba.crop((0,0,125,125))

        icon = im_rgba_crop.resize((125,125))

        img = Image.new("RGBA",(500,200),(70,70,70,255))
        d = ImageDraw.Draw(img)

        barre_xp = 200 + floor((xp/xp_level_suivant) * 175)
        d.rounded_rectangle([20,20,480,180],fill=(255,255,255,128),radius=5)
        d.rounded_rectangle([(200,130),(barre_xp ,150)],fill="red",radius=10)
        d.rounded_rectangle([(200,130),(450,150)],radius=10,width=3,outline="black")
        if len(member_name) > 12:
            d.text((200,105),text=member_name,font=FNT_20,fill=(0,0,0))
        else:
            d.text((200,100),text=member_name,font=FNT_30,fill=(0,0,0))
        d.text((370,25),text=f"Level : {level}",font=FNT_25,fill=(0,0,0))
        d.text((370,50),text=f"Rank : #{rank}",font=FNT_25,fill=(0,0,0))
        d.text((380,100),text=f"{xp}/{xp_level_suivant}xp",font=FNT_25,fill=(0,0,0))
        img.paste(icon,(50,40),icon)
        img.save(f"avatars/{member_id}_rank_card.png")

    async def run_xp_card(self,member_id,member,rank,current_level,current_xp,next_level_xp):
        t = functools.partial(self.xpcard,member_id,member,rank,current_level,current_xp,next_level_xp)
        m = await bot.loop.run_in_executor(None,t)

    @commands.command()
    async def rank(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        member_id = member.id
        table_name = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/xp.db") as db:
            cursor = await db.execute(f"SELECT current_xp,next_level_xp,current_level FROM {table_name} WHERE member_id = ?",(member_id,))
            result = await cursor.fetchone()
            if result:
                await member.avatar_url.save(f"avatars/{member_id}_avatar.png")
                await self.run_xp_card(member_id,str(member),10,result[2],result[0],result[1])
                await ctx.send(file=discord.File(f"avatars/{member_id}_rank_card.png"))
                os.remove(f"avatars/{member_id}_avatar.png")
                os.remove(f"avatars/{member_id}_rank_card.png")
            else:
                return await ctx.send("This member never spoke in the chat. How scary it is. Or they spoke in a channel I don't have access to. Either way, this ain't cool.")

    @commands.command(aliases=["levels"])
    async def ranking(self,ctx):
        l = []
        table_name = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/xp.db") as db:
            async with db.execute(f"SELECT member_id,current_level FROM {table_name} ORDER BY current_level DESC,current_xp DESC;") as cursor:
                async for row in cursor:
                    member = ctx.guild.get_member(row[0])
                    l.append(f"• {member}. Level : {row[1]}")
        embed = discord.Embed(title=f"{ctx.guild}'s ranking".capitalize(),color=0x03fcc6,timestamp=datetime.utcnow(),description="\n".join(l))
        await ctx.send(embed=embed)

    @commands.group()
    @commands.has_permissions(administrator=True)
    async def reset(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Subcommand required.")

    @reset.command()
    async def all(self,ctx):
        try:
            await ctx.send("This will delete E.V.E.R.Y existing datas about your rank. No backup possible ! Type 'yes' to continue.")
            confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                table_name = f"_{ctx.guild.id}"
                async with aiosqlite.connect("databases/xp.db") as db:
                    await db.execute(f"DELETE FROM {table_name};")
                    await db.commit()
    
    @reset.command()
    async def member(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        try:
            await ctx.send(f"This will reset {member} levels. No backup possible ! Type 'yes' to continue.")
            confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                table_name = f"_{ctx.guild.id}"
                async with aiosqlite.connect("databases/xp.db") as db:
                    await db.execute(f"DELETE FROM {table_name} WHERE member_id = ?;",(member.id,))
                    await db.commit()

class OwnerOnly(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def spam(ctx,member:discord.Member=None):
        member = member or ctx.author
        for i in range(50):
            await ctx.send(member.mention)
        await ctx.channel.purge(limit=51)

    @commands.command()
    async def guild_id(self,ctx):
        await ctx.send(f"Guild id : {ctx.guild.id}")

    @commands.command()
    async def member_id(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        await ctx.send(f"{member}'s ID : {member.id}")
    
    @commands.command()
    async def cogs(self,ctx):
        await ctx.send(", ".join(self.bot.cogs.keys()))
    
    @commands.command()
    async def guildbyid(self,ctx,id:int):
        guild = self.bot.get_guild(id)
        await ctx.send(guild)


@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.command()
async def echo(ctx,*,args):
    await ctx.send(args)



bot.add_cog(ChuckNorris(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(Music(bot))
bot.add_cog(Tags(bot))
bot.add_cog(ErrorHandler(bot))
bot.add_cog(Poll(bot))
bot.add_cog(Logs(bot))
bot.add_cog(CustomPrefixes(bot))
bot.add_cog(OwnerOnly(bot))
bot.add_cog(CustomOnMessage(bot))
bot.add_cog(XPSystem(bot))
bot.run(TOKEN)

