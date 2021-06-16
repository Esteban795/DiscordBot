import aiosqlite
import asyncio
import discord
from discord.ext import commands
from bot import TimeConverter,get_prefix

class Moderation(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    async def bot_check(self, ctx):
        """
        This check does two things.
        
        1) It checks if the message was called from a guild. If not, this raises an error.
        2) It checks if either the channel is allowed to call commands OR if the member that tried using commands is able to. If not, it raises 2 differents errors to make it clear.
        """
        if not ctx.guild:
            raise commands.NoPrivateMessage("This bot doesn't work on DM channels.")
        async with aiosqlite.connect("databases/main.db") as db:
            cursor = await db.execute("SELECT * FROM ignored_channels WHERE channel_id = ?",(ctx.channel.id,))
            res_channel = await cursor.fetchone()
            cursor = await db.execute("SELECT * FROM ignored_members WHERE member_id = ? AND guild_id = ?",(ctx.author.id,ctx.guild.id))
            res_member = await cursor.fetchone()
        if res_channel:
            raise commands.DisabledCommand("You can't use commands in this channel.")
        if res_member:
            raise commands.DisabledCommand("You are not allowed to use commands on this server.")
        return True

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        """
        1) Checks if the guild has a Muted/muted role. If the role doesn't exist, it creates it and disables send_messages/speak permissions.
        2) Creates a warn table.
        """
        existing_muted_role = discord.utils.get(guild.roles,name="muted") or discord.utils.get(guild.roles,name="Muted")
        if not existing_muted_role:
            mutedRole = await guild.create_role(name="Muted",permissions=discord.Permissions(send_messages=False,speak=False))
            for channel in guild.channels:
                await channel.set_permissions(mutedRole, send_messages = False, speak = False)
        async with aiosqlite.connect("databases/warns.db") as db:
            await db.execute(f"CREATE TABLE IF NOT EXISTS _{guild.id}(member_id INT,nb_warnings INT)")
            await db.execute(f"INSERT INTO _{guild.id} VALUES(0,5);")
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
        await ctx.send(f"{user} was unmuted.")

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
    async def match(self,ctx,reason,*,words):
        """Bans every member that said [words] in the last 100 messages of this channel. Reason must be quoted if it isn't a single word"""
        banned_words = words.split(",") #Split the words if there are more than one
        last_100_messages = await ctx.channel.history(limit=123).flatten() #Is a list of last 100 messages from this channel.
        count = 0
        for message in last_100_messages:
            if message.author == ctx.author or message.author.bot: #Bots won't be banned, and the person who called this command won't either. So go to the next message
                continue
            for word in banned_words:
                if word in message.content: #If a banned word is inside the message
                    embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
                    embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await message.author.send(embed=embedVar)
                    await message.author.ban(reason=reason)
                    count += 1
                    break #No needs to know if there are two words that could make you banned in the message. One is enough
        if count:
            await ctx.send((f'Done ! I banned {count} people.' if count > 1 else "Done ! I banned one person."))
        else:
            await ctx.send("No one said those awful words.")

    @ban.group(invoke_without_command=True)
    async def time(self,ctx,member:discord.Member,time:TimeConverter,*,reason="Not specified."):
        """Basically a ban command where you can add a duration. Once it's over, the bot automatically unbans the member"""
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
        """Bans every member that said [words] in the last 100 messages of this channel for a [time] duration. Reason must be quoted if it isn't a single word"""
        banned_words = words.split(" ")
        last_100_messages = await ctx.channel.history(limit=123).flatten()
        banned_people = [] #will store discord.Member objects
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
        for i in banned_people: #Once the ban duration is over, iterate through the list of banned people and then unban them.
            await i.unban()


    @commands.command(aliases=["u","unbna"])
    @commands.has_permissions(ban_members = True)
    async def unban(self,ctx,person,*,reason="Not specified."):
        """Unbans the member from the guild"""
        bans = await ctx.guild.bans()
        if len(bans) == 0: #Checks if the banlist is empty.
            embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
            return await ctx.send(embed=embedVar)
        elif person == "all":
            for entry in bans:
                user = await  self.bot.fetch_user(entry.user.id)
                await ctx.guild.unban(user)
                embedVar = discord.Embed(title="All members have been successfully unbanned !",color=0xaaffaa)
                return await ctx.send(embed=embedVar)
        count = 0
        dictionary = dict()
        string = ""
        continuer = True
        for entry in bans:
            if "{0.name}#{0.discriminator}".format(entry.user) == person:
                user = await self.bot.fetch_user(entry.user.id)
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
                ans = await self.bot.wait_for('message',check=check, timeout=10)
                try:
                    emoji = '\u2705'
                    lines = string.split("\n")
                    identifier = int(dictionary[lines[int("{0.content}".format(ans)) - 1]])
                    user = await self.bot.fetch_user(identifier)
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
        """Sends you in DM the permissions the member has on the server."""
        embedVar = discord.Embed(title=f"You asked for {member}'s permissions on {ctx.guild}.",color=0xaaaaff)
        embedVar.add_field(name="Here they are : ",value="\n".join(["• {}".format(i[0]) for i in member.guild_permissions if i[1] is True])) #Iterate through the discord.Member permissions on the guild. If they have the permission, this is added to the list.
        await ctx.author.send(embed=embedVar)

    @commands.group(invoke_without_command=True)
    async def warn(self,ctx,member:discord.Member,*,reason=None):
        """
        With no subcommand passed : 

        1) It connects to the database and check if the member already has warnings. It also stores the number of warns allowed for the server you're in. Default is 5.
        2) If the member has warnings, we increment the number of warnings they have.
            - the number of warnings goes above the limit allowed not to be under sanctions : the member gets kicked, their number of warnings get reset.
            - the number of warnings stay under the limit allowed : we just increment the amount of warnings they have.
        3) If the member has no warnings, we create a new row and add it to the database.
        """
        if ctx.invoked_subcommand is None:
            table_name = f"_{ctx.guild.id}"
            async with aiosqlite.connect("databases/warns.db") as db:
                cursor =  await db.execute(f"SELECT nb_warnings FROM {table_name}  WHERE member_id = ?",(member.id,))
                result = await cursor.fetchone()
                number_of_warns_allowed = await db.execute(f"SELECT nb_warnings FROM {table_name} WHERE member_id = 0;") #Number of warns allowed for everyone on the server. You can update it whenever you want.
                res = await number_of_warns_allowed.fetchone()
                if result:   #The member already has warnings
                    new_warns_number = result[0] + 1
                    if new_warns_number >= int(res[0]): #The member reached the maximum number of warnings allowed without being kicked.
                        await db.execute(f"DELETE FROM {table_name} WHERE member_id = ?;",(member.id,))
                        await db.commit()
                        await member.kick(reason=reason)
                        await ctx.send(f"{member} was kicked due to too many warns !")
                    else: #Just increment the amount of warnings the member has
                        await db.execute(f"UPDATE {table_name} SET nb_warnings = ? WHERE member_id = ?",(new_warns_number,member.id))
                        await db.commit()
                else: #Member doesn't have any warnings
                    await db.execute(f"INSERT INTO {table_name} VALUES(?,1);",(member.id,)) #We create their row
                    await db.commit()
    
    @warn.command()
    async def changenumber(self,ctx,amount:int):
        """
        This allows you to change the number of warnings required to get kicked from the guild.

        1) Retrieves the current amount of warnings allowed from the database.
        2) Ask you to confirm you want this number to change. 
        /!\ If you change this limit to a smaller one, members with number of warnings ABOVE the new limit will only get kicked with their next warning.

        3) If you confirm, it changes it. If you take too much time to answer, it cancels the process.
        """
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
        """A softban is a kick that allows you to delete every message the member has sent on your server.
        
        1) We ban the member from the guild.
        2) We immediately unban them.
        """
        await member.ban(reason=reason)
        await member.unban(reason=reason)
        await ctx.send(f"{member} was softbanned.")

    @commands.group(invoke_without_command=True)
    async def ignore(self,ctx):
        """This command requires subcommand to work. Nothing much to add to this.."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use the 'member' or 'channel' subcommand to specify who shouldn't be allowed to use a command, or where people won't be allowed to use those beautiful commands !")

    @ignore.command(name="member")
    async def _m(self,ctx,member:discord.Member=None):
        """Ignore the commands from a member on a specific server. This means that they won't be able to use commands on this server but they will on another.

        1) Checks if the member is already ignored. If they are :
            - bot asks you if you want to allow them to use commands. Type 'yes' to remove the ignore status on them.
        2) If the member can currently use commands, they are now disabled for them.
        """
        async with aiosqlite.connect("databases/main.db") as db:
            cursor = await db.execute("SELECT member_id FROM ignored_members WHERE member_id = ? AND guild_id = ?",(member.id,ctx.guild.id)) 
            result = await cursor.fetchone()
            if result: #Is member already ignored
                await ctx.send("This member is already ignored. Type 'yes' if you want them to be able to use commands on this server !")
                try: #Confirm
                    confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
                except asyncio.TimeoutError:
                    await ctx.send("You didn't answer fast enough. Aborting the process !")
                else:
                    if confirm.content.lower() == "yes": #confirmation
                        await db.execute("DELETE FROM ignored_members WHERE member_id = ? AND guild_id = ?",(member.id,ctx.guild.id))
                        await db.commit()
                        await ctx.send(f"{member.mention} now has enabled commands !")
            else:
                await db.execute("INSERT INTO ignored_members VALUES(?,?);",(member.id,ctx.guild.id))
                await db.commit()
                await ctx.send(f"{member.mention} now has disabled commands !")

    @ignore.command()
    async def channel(self,ctx,channel:discord.TextChannel=None):
        """
        Ignore the commands from a channel on a server. This means that nobody will be able to use commands in this channel.

        1) Same as member. If the channel is already ignored, then you can delete it by typing 'yes'.
        2) Else,if the channel has commands enabled, it disables them from now on and says every time someone tries to use a command that commands aren't available on this channel
        """
        async with aiosqlite.connect("databases/main.db") as db:
            cursor = await db.execute("SELECT channel_id FROM ignored_channels WHERE channel_id = ?",(channel.id,))
            result = await cursor.fetchone()
            if result: #is channel already ignored
                await ctx.send("This channel is already ignored. Type 'yes' if you want people to be able to use commands there !")
                try: #Confirm
                    confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
                except asyncio.TimeoutError:
                    await ctx.send("You didn't answer fast enough. Aborting the process !")
                else:
                    if confirm.content.lower() == "yes": #confirm 
                        await db.execute("DELETE FROM ignored_channels WHERE channel_id = ?",(channel.id,))
                        await db.commit()
                        await ctx.send(f"{channel.mention} now has enabled commands !")
                    else:
                        await ctx.send("Aborting process !")
            else:
                await db.execute("INSERT INTO ignored_channels VALUES(?);",(channel.id,))
                await db.commit()
                await ctx.send(f"{channel.mention} now has disabled commands !")

    @commands.group(invoke_without_command=True)
    async def purge(self,ctx,Amount:int=2): #Delete "Amount" messages from the current channel. $purge [int]
        """
        Deletes a certain amount of message from the channel the command is used in. This command can have more detailed purge options, with the subcommands.

        Usage example : $purge 10
        This will delete the last 10 messages from the channel.
        """
        await ctx.message.delete()
        if ctx.invoked_subcommand is None:
            await ctx.channel.purge(limit=int(Amount))
    
    @purge.command()
    async def commands(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.
        1) Get the guild custom prefixes (if they exist. Else, only '$' will be matched as a prefix). 
        BE CAREFUL : this command only allows you to delete the commands called with either '$' or the guild custom prefixes. 
        This means that any command from another bot won't be detected as such and thus not deleted.

        Conditions : 
        - Message's author is a bot OR message starts with a server prefix.
        """
        guild_prefix = tuple(await get_prefix(self.bot,ctx.message))
        await ctx.channel.purge(limit=amount,check=lambda m:m.author.bot or m.content.startswith(guild_prefix))
 
    @purge.command()
    async def bots(selt,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : the message's author is a bot.
        """
        await ctx.channel.purge(limit=amount,check=lambda m:m.author.bot)
        await ctx.message.delete()
    
    @purge.command()
    async def humans(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : the message's author is NOT a bot AND the message doesn't call a command.
        """
        guild_prefix = tuple(await get_prefix(self.bot,ctx.message))
        await ctx.channel.purge(limit=amount,check=lambda m:not (m.author.bot or m.content.startswith(guild_prefix)))
    
    @purge.command()
    async def member(self,ctx,amount:int=2,member:discord.Member=None):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : the message's author is NOT a bot.
        """
        member = member or ctx.author
        await ctx.channel.purge(limit=amount,check=lambda m:m.author == member)
        await ctx.message.delete()
    
    @purge.command()
    async def match(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : [content] is in the message.
        """
        await ctx.channel.purge(limit=amount,check=lambda m:content in m.content)
    
    @purge.command(name="not")
    async def _not(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : [content] is NOT in the message.
        """
        await ctx.channel.purge(limit=amount,check=lambda m:not (content in m.content))
        await ctx.message.delete()
    
    @purge.command()
    async def startswith(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : message starts with [content] .
        """
        await ctx.channel.purge(limit=amount,check=lambda m:m.content.startswith(content))
        await ctx.message.delete()
    
    @purge.command()
    async def endswith(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : message ends with [content].
        """
        await ctx.channel.purge(limit=amount,check=lambda m:m.content.endswith(content))
        
    @purge.command()
    async def embeds(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : message is an embed.
        """
        await ctx.channel.purge(limit=amount,check=lambda m:len(m.embeds))
        await ctx.message.delete()

    @purge.command()
    async def images(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.
        This one is not fully accurate 
        Conditions : message ends with [content].
        """
        await ctx.channel.purge(limit=amount,check=lambda m:len(m.attachments) or m.content.startswith(("https://cdn.discordapp.com/attachments/","https://tenor.com/view/")))
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Moderation(bot))