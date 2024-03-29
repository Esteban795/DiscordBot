import asyncio
import discord
from discord.errors import Forbidden, HTTPException
from discord.ext import commands,tasks
from bot import TimeConverter,get_prefix
import datetime

class Moderation(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.ignored_channels = set()
        self.ignored_members = dict()
        self.bot.loop.create_task(self._cache_ignored_members())
        self.bot.loop.create_task(self._cache_ignored_channels())
        self.unban_loop.start()
        self.unmute_loop.start()

    async def _cache_ignored_members(self):
        """Internal process to cache the ignored members' ids."""
        await self.bot.wait_until_ready()
        async with self.bot.db.execute("SELECT * FROM ignored_members") as cursor:
            result = await cursor.fetchall()
        for member_id,guild_id in result:
            try:
                self.ignored_members[guild_id].add(member_id)
            except KeyError:
                self.ignored_members[guild_id] = set([member_id])
        return

    async def _cache_ignored_channels(self):
        """Internal process to cache the ignored channels' ids."""
        await self.bot.wait_until_ready()
        async with self.bot.db.execute("SELECT * FROM ignored_channels") as cursor:
            result = await cursor.fetchall()
        for channel_id in result:
            self.ignored_channels.add(channel_id[0])
        return

    async def unban_task(self,unbanning):
        """
        Sleeps until unban_time, then unban the user.
        """
        ban_id,member_id,guild_id,unban_time = unbanning
        t = datetime.datetime.strptime(unban_time,"%Y-%m-%d %H:%M:%S")
        await discord.utils.sleep_until(unban_time)
        guild = self.bot.get_guild(guild_id)
        if guild.unavailable:
            return
        if guild is None:
            await self.bot.db.execute("DELETE FROM bans WHERE guild_id = ?",(guild_id,)) #Guild not cached anymore, most likely bot left the guild
            await self.bot.db.commit()
            return
        banned = discord.Object(id=member_id)
        try:
            await guild.unban(banned,reason="Ban duration is up.")
        except discord.NotFound:
            await self.bot.db.execute("DELETE FROM bans WHERE ban_id = ?",(ban_id,))
        else:
            await self.bot.db.execute("UPDATE bans SET unbanned = 1,unban_reason = 'Ban duration is up' WHERE ban_id = ?",(ban_id,))            
        await self.bot.db.commit()
        
    @tasks.loop(seconds=30)
    async def unban_loop(self):
        """Checks every 30 seconds if a ban ends within 30 seconds"""
        await self.bot.wait_until_ready()
        sql = "SELECT ban_id,member_id,guild_id,unban_time FROM bans WHERE unban_time IS NOT NULL AND unbanned = 0 AND CAST((julianday(unban_time) - julianday('now'))*86400 AS INTEGER) <= 30"
        async with self.bot.db.execute(sql) as cursor:
            async for row in cursor:
                await self.unban_task(row)
                
    async def unmute_task(self,unmuting):
        """
        Sleeps until unmute_time, then unmute the user.
        """
        mute_id,member_id,guild_id,unmute_time = unmuting
        t = datetime.datetime.strptime(unmute_time,"%Y-%m-%d %H:%M:%S")
        await discord.utils.sleep_until(t) #Sleeps until datetime
        guild = self.bot.get_guild(guild_id)
        if guild.unavailable:
            return
        if guild is None:
            await self.bot.db.execute("DELETE FROM mutes WHERE guild_id = ?",(guild_id,))
            await self.bot.db.commit()
            return
        muted_role = discord.utils.get(guild.roles,name="Muted") or discord.utils.get(guild.roles,name="muted")
        if not muted_role:
            return await self.bot.db.execute("UPDATE mutes SET unmuted = 1,unmute_reason = 'Role Muted doesn't exist.' WHERE mute_id = ?",(mute_id,))
        member = guild.get_member(member_id)
        if not member:
            await self.bot.db.execute("UPDATE mutes SET unmuted = 1,unmute_reason = 'Couldn't find the member' WHERE mute_id = ?",(mute_id,))
            return await self.bot.db.commit()
        try:
            await member.remove_roles(muted_role)
        except discord.Forbidden:
            await guild.owner.send(f"Couldn't unmute {member}. My role is below them.")
        else:
            await self.bot.db.execute("UPDATE mutes SET unmuted = 1,unmute_reason = 'Mute duration is up.' WHERE mute_id = ?",(mute_id,))
            return await self.bot.db.commit()
            
    @tasks.loop(seconds=30)
    async def unmute_loop(self):
        await self.bot.wait_until_ready()
        sql = "SELECT mute_id,member_id,guild_id,unmute_time FROM mutes WHERE unmute_time IS NOT NULL AND CAST((julianday(unmute_time) - julianday('now'))*86400 AS INTEGER) <= 30 AND unmuted = 0;"
        async with self.bot.db.execute(sql) as cursor:
            async for row in cursor:
                await self.unmute_task(row)

    def bot_has_higher_role(self,member):
        if member.top_role.position < member.guild.me.top_role.position:
            return True
        raise commands.CheckFailure(f"Check failed : {member.mention}'s top role position is higher than mine. Thus I can't perform the command !")

    async def bot_check(self, ctx):
        """
        This check does two things.
        
        1) It checks if the message was called from a guild. If not, this raises an error.
        2) It checks if either the channel is allowed to call commands OR if the member that tried using commands is able to. If not, it raises 2 differents errors to make it clear.
        """
        if not ctx.guild:
            raise commands.NoPrivateMessage("This bot doesn't work on DM channels.")
        if ctx.author.guild_permissions.administrator: #Bypass for ignored members/channels
            return True
        if ctx.channel.id in self.ignored_channels:
            raise commands.DisabledCommand("You can't use commands in this channel.")
        try:
            if ctx.author.id in self.ignored_members[ctx.guild.id]:
                raise commands.DisabledCommand("You are not allowed to use commands on this server.")
        except KeyError: #The guild doesn't have ignored members, so we can just skip it
            return True
        return True
        
    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        """
        1) Checks if the guild has a Muted/muted role. If the role doesn't exist, it creates it and disables send_messages/speak permissions.
        2) Creates a warn_allowed row for each guild, which allows us to change the number of warns allowed for each member before getting kicked.
        """
        existing_muted_role = discord.utils.get(guild.roles,name="muted") or discord.utils.get(guild.roles,name="Muted")
        if not existing_muted_role:
            muted_role = await guild.create_role(name="Muted",permissions=discord.Permissions(send_messages=False,speak=False,add_reactions=False))
            for channel in guild.channels:
                await channel.set_permissions(muted_role, send_messages = False, speak = False)
            await self.bot.db.execute(f"INSERT OR ABORT INTO warns_allowed VALUES(?,5,'kick');",(guild.id,))
            await self.bot.db.commit()
        for member in guild.members:
            for role in member.roles:
                await self.bot.db.execute("INSERT OR IGNORE INTO roles VALUES(?,?,?)",(member.id,guild.id,role.id))
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_member_join(self,member):
        already_joined = await self.bot.db.execute("SELECT role_id FROM roles WHERE guild_id = ? AND member_id = ?",(member.guild.id,member.id))
        result = await already_joined.fetchall()
        if result:
            roles = [member.guild.get_role(role[0]) for role in result if role in member.guild.roles if self.bot_has_higher_role(member)]
            await member.edit(roles=roles)

    @commands.Cog.listener()
    async def on_member_update(self,before,after):
        if before.roles != after.roles:
            diff_roles_id = [role.id for role in set(before.roles)^set(after.roles)]
            for role_id in diff_roles_id:
                exists = await self.bot.db.execute("SELECT role_id FROM roles WHERE member_id = ? AND guild_id = ? AND role_id = ?",(before.id,before.guild.id,role_id))
                result = await exists.fetchone()
                if result:
                    await self.bot.db.execute("DELETE FROM roles WHERE member_id = ? AND guild_id = ? AND role_id = ?",(before.id,before.guild.id,role_id))
                else:
                    await self.bot.db.execute("INSERT INTO roles VALUES(?,?,?)",(before.id,before.guild.id,role_id))
            await self.bot.db.commit()
            
    @commands.Cog.listener()
    async def on_guild_remove(self,guild:discord.Guild):
        """When the bot leaves/gets kicked from a guild, no needs to store the warns since they are server dependent"""
        await self.bot.db.execute("DELETE FROM warns_allowed WHERE guild_id = ?",(guild.id))
        await self.bot.db.execute("DELETE FROM warns WHERE guild_id = ?",(guild.id))
        await self.bot.db.commit()
    
    @commands.command(aliases=["addrole","roleadd"],help="Lets you add a role to a member.")
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True) #Check if the member of this guild has the permissions to manage roles.
    async def giverole(self,ctx,member:discord.Member,role:discord.Role):
        """Gives the member you mentionned a role"""
        if self.bot_has_higher_role(member):
            await member.add_roles(role)
            embedVar = discord.Embed(description=f"{member} was granted the {role} role.",color=0xaaffaa)
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        
    @commands.command(aliases=["rmvrole"],help="Removes a role from the member.")
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles = True)
    async def removerole(self,ctx,member : discord.Member, role:discord.Role):
        """Removes a role from the member you mentionned"""
        if self.bot_has_higher_role(member):
            await member.remove_roles(role)
            embedVar = discord.Embed(description=f"{member} lost the {role} role.",color=0xaaffaa)
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)

    @commands.command(aliases=["gtfo"],help="Kicks a member from the guild.")
    @commands.has_permissions(kick_members = True)
    async def kick(self,ctx, member: discord.Member, *,reason="Not specified."):
        """Sends [member] a DM telling them they got kicked from the server you're in with the reason (if you told one)"""
        if self.bot_has_higher_role(member):
            await member.kick(reason=reason)
            embedVar = discord.Embed(description=f"{member} was successfully kicked from the server.",color=0xaaffaa) #Confirms everything went okay
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)

    @commands.command(help="Mutes a member for the inputted duration. If the member was already muted, it adds the previous duration to this one.")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self,ctx,member:discord.Member,time:TimeConverter=None):
        """Gives [member] the Muted role (they can't speak or write) for (time) if you specified one. After the mute duration is over, it automatically demutes them"""
        muted_role = discord.utils.get(ctx.guild.roles,name="Muted") or discord.utils.get(ctx.guild.roles,name="muted") #Get the discord.Role instance
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted",permissions=discord.Permissions(send_messages=False,speak=False,add_reactions=False))
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages = False, speak = False)
        if self.bot_has_higher_role(member):
            await member.add_roles(muted_role)
            await ctx.send(f"Muted {member} for {time}s" if time else f"Muted {member}")
            if time:
                mute_duration = datetime.timedelta(seconds=time)
                already_muted = await self.bot.db.execute("SELECT unmute_time FROM mutes WHERE member_id = ? AND guild_id = ?",(member.id,member.guild.id))
                result_already_muted = await already_muted.fetchone()
                if result_already_muted:
                    prev_unmute_time = datetime.datetime.strptime(result_already_muted[0],"%Y-%m-%d %H:%M:%S")
                    new_unmute_time = prev_unmute_time + mute_duration
                    await self.bot.db.execute("UPDATE mutes SET unmute_time = ? WHERE member_id = ? AND guild_id = ?",(new_unmute_time.replace(microsecond=0),member.id,member.guild.id))
                else:
                    unmute_time = mute_duration + datetime.datetime.utcnow()
                    await self.bot.db.execute("INSERT INTO mutes(member_id,guild_id,unmute_time) VALUES(?,?,?);",(member.id,member.guild.id,unmute_time.replace(microsecond=0)))
                await self.bot.db.commit()

    @commands.command(aliases=["demute"],help="Unmute a member,no matter the duration.")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self,ctx,member:discord.Member,*,reason="Moderator."):
        """Removes the Muted role from the member. They now have the permission to speak/write"""
        muted_role = discord.utils.get(ctx.guild.roles,name="Muted") or discord.utils.get(ctx.guild.roles,name="muted")
        if not muted_role:
            return await ctx.send("Muted role doesn't exist. Mute someone to automatically create it !")
        if self.bot_has_higher_role(member):
            await member.remove_roles(muted_role)
            await ctx.send(f"{member} was unmuted.")
            await self.bot.db.execute("UPDATE mutes SET done = 1, unmute_reason = ? WHERE member_id = ? and guild_id = ?",(reason,member.id,ctx.guild.id))
            await self.bot.db.commit()
            
    @commands.command(aliases=["banl","bl"])
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
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

    @commands.group(invoke_without_command=True,help="Bans a member from the guild. You can input a reason or not, depends on you !")
    @commands.has_permissions(ban_members = True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def ban(self,ctx,member:discord.Member,*,reason="Not specified."):
        """Bans a member from the server. This is a group, which means you CAN use subcommands for more specific ban options. 
        The current command just bans a member from the server, and sends them a DM with the reason they got banned"""
        if self.bot_has_higher_role(member):
            if ctx.invoked_subcommand is None: #Check if a subcommand is passed in.
                try:
                    await member.ban(reason=reason)
                except HTTPException:
                    return await ctx.send("Unknow error occured.")
                else:
                    await self.bot.db.execute("INSERT INTO bans(member_id,guild_id,ban_reason) VALUES(?,?,?)",(member.id,ctx.guild.id,reason))
                    await self.bot.db.commit()
                    return await ctx.send(f"Banned {member}.") 

    @ban.command(help="Bans a member that said any banned words in the last 100 messages. Reason must be quoted if more than s single word.")
    async def match(self,ctx,reason,*banned_words):
        """Bans every member that said [words] in the last 100 messages of this channel. Reason must be quoted if it isn't a single word"""
        last_100_messages = await ctx.channel.history(limit=100).flatten() #Is a list of last 100 messages from this channel.
        count = 0
        for message in last_100_messages:
            if message.author == ctx.author or message.author.bot: #Bots won't be banned, and the person who called this command won't either. So go to the next message
                continue
            for word in banned_words:
                if word in message.content:
                    try:
                        await message.author.ban(reason=reason)
                    except Forbidden:
                        await ctx.send(f"Can't ban {message.author}. (Higher role)")
                    else:
                        await self.bot.db.execute("INSERT INTO bans(member_id,guild_id,ban_reason) VALUES(?,?,?)",(message.author.id,ctx.guild.id,reason))
                        await self.bot.db.commit()
                        count += 1
                        break
        if count:
            await ctx.send((f'Done ! I banned {count} people.' if count > 1 else "Done ! I banned one person."))
        else:
            await ctx.send("No one said those awful words.")

    @ban.group(invoke_without_command=True,help="Ban a user for a duration. Duration must be in the form of 1d, 12.5m etc..")
    async def time(self,ctx,member:discord.Member,time:TimeConverter,*,reason="Not specified."):
        """Basically a ban command where you can add a duration. Once it's over, the bot automatically unbans the member"""
        if ctx.invoked_subcommand is None:
            try:
                await member.ban(reason=reason)
            except Forbidden:
                await ctx.send(f"Can't ban {member}. (Higher role)")
            else:
                await ctx.send(f"Banned {member} for {time} seconds.")
                unban_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
                await self.bot.db.execute("INSERT INTO bans(member_id,guild_id,ban_reason,unban_time) VALUES(?,?,?,?)",(member.id,ctx.guild.id,reason,unban_time.replace(microsecond=0)))
                await self.bot.db.commit()
                await member.ban(reason=reason)

    @time.command(help="Bans a member for the duration, because they said a banned word in the last 100 message.")
    async def match(self,ctx,time:TimeConverter,reason,*banned_words):
        """Bans every member that said [words] in the last 100 messages of this channel for a [time] duration. Reason must be quoted if it isn't a single word"""
        last_100_messages = await ctx.channel.history(limit=100).flatten() #Is a list of last 100 messages from this channel.
        count = 0
        for message in last_100_messages:
            if message.author == ctx.author or message.author.bot: #Bots won't be banned, and the person who called this command won't either. So go to the next message
                continue
            for word in banned_words:
                if word in message.content:
                    try:
                        await message.author.ban(reason=reason)
                    except Forbidden:
                        await ctx.send(f"Can't ban {message.author}. (Higher role)")
                    else:
                        unban_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
                        await self.bot.db.execute("INSERT INTO bans(member_id,guild_id,reason,unban_time) VALUES(?,?,?)",(message.author,ctx.guild.id,reason,unban_time.replace(microsecond=0)))
                        await self.bot.db.commit()
                        count += 1
                        break
        if count:
            await ctx.send((f'Done ! I banned {count} people.' if count > 1 else "Done ! I banned one person."))
        else:
            await ctx.send("No one said those awful words.")

    @commands.command(aliases=["u","uban"],help="Unbans a user. You can either use their ID or their name + discriminator.")
    async def unban(self,ctx,user:discord.User):
        try:
            await ctx.guild.unban(user)
        except discord.NotFound:
            raise
        else:
            return await ctx.send(f"Unbanned {user}")


    @commands.command(aliases=["p","perms"],help="Sends you (in DM if allowed, else in the channel) the permissions a member has in this server.")
    @commands.has_permissions(administrator = True)
    async def permissions(self,ctx,member:discord.Member):
        """Sends you in DM the permissions the member has on the server."""
        embedVar = discord.Embed(title=f"You asked for {member.mention}'s permissions on {ctx.guild}.",color=0xaaaaff)
        embedVar.add_field(name="Here they are : ",value="\n".join(["• {}".format(i[0]) for i in member.guild_permissions if i[1] is True])) #Iterate through the discord.Member permissions on the guild. If they have the permission, this is added to the list.
        try:
            await ctx.author.send(embed=embedVar)
        except discord.Forbidden:
            await ctx.send(embed=embedVar)

    @commands.group(invoke_without_command=True,help="Warns a user. If they have 5 or more warns, they get automatically kicked (or banned). You can change the limit, and the punishment !")
    @commands.has_permissions(ban_members=True)
    async def warn(self,ctx,member:discord.Member,*,reason=None):
        """
        With no subcommand passed : 

        1) It connects to the database and check if the member already has warnings. It also stores the number of warns allowed for the server you're in. Default is 5.
        2) If the member has warnings, we increment the number of warnings they have.
            - the number of warnings goes above the limit allowed not to be under sanctions : the member gets kicked, their number of warnings get reset. (default)
            - the number of warnings stay under the limit allowed : we just increment the amount of warnings they have.
        3) If the member has no warnings, we create a new row and add it to the database.
        """
        true_reason = reason + "(Too many warns)"
        if ctx.invoked_subcommand is None:
            cursor =  await self.bot.db.execute(f"SELECT nb_warnings FROM warns  WHERE member_id = ? AND guild_id = ?",(member.id,ctx.guild.id))
            result = await cursor.fetchone()
            n_member_warnings = result[0]
            number_of_warns_allowed = await self.bot.db.execute(f"SELECT n,punishment FROM warns_allowed WHERE guild_id = ?",(ctx.guild.id,)) #Number of warns allowed for everyone on the server. You can update it whenever you want.
            res = await number_of_warns_allowed.fetchone()
            number_of_warns_allowed = res[0]
            punishment = res[1]
            if result:   #The member already has warnings
                new_warns_number = n_member_warnings + 1
                if new_warns_number > number_of_warns_allowed: #The member reached the maximum number of warnings allowed without being kicked.
                    await self.bot.db.execute(f"DELETE FROM warns WHERE member_id = ? AND guild_id = ?;",(member.id,ctx.guild.id))
                    await self.bot.db.commit()
                    if punishment == "kick":
                        try:
                            await member.kick(reason=true_reason)
                        except discord.Forbidden:
                            return await ctx.send(f"Can't kick {member.mention} (most likely due to their top role being higher than mine).")
                        else:
                            return await ctx.send(f"Successfully kicked {member.mention} (due to too many warns).")
                    else:
                        try:
                            await member.ban(reason=true_reason)
                        except discord.Forbidden:
                            return await ctx.send(f"Can't ban {member.mention} (most likely due to their top role being higher than mine).")
                        else:
                            return await ctx.send(f"Successfully banned {member.mention} (due to too many warns).")
                else: #Just increment the amount of warnings the member has
                    await self.bot.db.execute(f"UPDATE warns SET nb_warnings = ? WHERE member_id = ? AND guild_id = ?",(new_warns_number,member.id,ctx.guild.id))
                    await self.bot.db.commit()
            else: #Member doesn't have any warnings
                await self.bot.db.execute(f"INSERT INTO warns VALUES(?,?,1);",(member.id,ctx.guild.id)) #We create their row
                await self.bot.db.commit()
    
    @warn.command(help="Allows you to change the limit of warns required to be under punishments, such as ban or kick.")
    async def changenumber(self,ctx,amount:int):
        """
        This allows you to change the number of warnings required to get kicked from the guild.

        1) Retrieves the current amount of warnings allowed from the database.
        2) Ask you to confirm you want this number to change. 
        /!\ If you change this limit to a smaller one, members with number of warnings ABOVE the new limit will only get kicked with their next warning.

        3) If you confirm, it changes it. If you take too much time to answer, it cancels the process.
        """
        cursor = await self.bot.db.execute(f"SELECT n,punishment FROM warns_allowed WHERE guild_id = ?",(ctx.guild.id,))
        res = await cursor.fetchone()
        try:
            await ctx.send(f"Currently, {res[0]} warning(s) gets you auto-{res[1]}ed. Are you sure you want to change that to {amount} ?")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute(f"UPDATE warns SET nb_warnings = ? WHERE member_id = 0;",(amount,))
                await self.bot.db.commit()

    @warn.command(help="Allows you to change the punishment that will happen if a member goes above the warn limit.")
    async def changepunishment(self,ctx,new_punishment:str):
        if new_punishment not in {"kick","ban"}:
            return await ctx.send("The punishment must be 'kick' or 'ban'.")
        try:
            await ctx.send("Are you sure you want to change the punishment ?")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            await self.bot.db.execute("UPDATE warns_allowed SET punishment = ? WHERE guild_id = ?",(new_punishment,ctx.guild.id))
            await self.bot.db.commit()
            return await ctx.send(f"New punishment for exceeding number of warns allowed : {new_punishment}.")

    @commands.command(help="Softbans the user. This means they are banned, and immediately unbanned. This is a shorter way than kick + purge message !")
    async def softban(self,ctx,member:discord.Member,*,reason):
        """A softban is a kick that allows you to delete every message the member has sent on your server.
        
        1) We ban the member from the guild.
        2) We immediately unban them.
        """
        await member.ban(reason=reason)
        await member.unban(reason=reason)
        await ctx.send(f"{member.mention} was softbanned.")

    @commands.group(invoke_without_command=True,help="Main command of the ignore channels/members features. Does nothing without those subcommands.")
    async def ignore(self,ctx):
        """This command requires subcommand to work. Nothing much to add to this.."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use the 'member' or 'channel' subcommand to specify who shouldn't be allowed to use a command, or where people won't be allowed to use those beautiful commands !")

    @ignore.command(name="member",help="Allows you to ignore/unignore a member. This means the bot won't/will listen for their commands.")
    async def _m(self,ctx,member:discord.Member=None):
        """Ignore the commands from a member on a specific server. This means that they won't be able to use commands on this server but they will on another.

        1) Checks if the member is already ignored. If they are :
            - bot asks you if you want to allow them to use commands. Type 'yes' to remove the ignore status on them.
        2) If the member can currently use commands, they are now disabled for them.
        """
        async def _ignore_member():
            await self.bot.db.execute("INSERT INTO ignored_members VALUES(?,?);",(member.id,ctx.guild.id))
            await self.bot.db.commit()
            try:
                self.ignored_members[ctx.guild.id].add(member.id)
            except KeyError:
                self.ignored_members[ctx.guild.id] = {member.id}
            return await ctx.send(f"{member.mention} now has disabled commands !",allowed_mentions=self.bot.no_mentions)
        try:
            is_member_banned = member.id in self.ignored_members[ctx.guild.id]
        except KeyError:
            await _ignore_member()
        else:
            if is_member_banned:
                await ctx.send("This member is already ignored. Type 'yes' if you want them to be able to use commands on this server !")
                try: #Confirm
                    confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
                except asyncio.TimeoutError:
                    await ctx.send("You didn't answer fast enough. Aborting the process !")
                else:
                    if confirm.content.lower() == "yes": #confirmation
                        await self.bot.db.execute("DELETE FROM ignored_members WHERE member_id = ? AND guild_id = ?",(member.id,ctx.guild.id))
                        await self.bot.db.commit()
                        self.ignored_members[ctx.guild.id].remove(member.id)
                        await ctx.send(f"{member.mention} now has enabled commands !")
            else:
                await _ignore_member()

    @ignore.command(help="Allows you to ignore/unignore a channel. This means the bot won't/will listen for commands in this channel.")
    async def channel(self,ctx,channel:discord.TextChannel=None):
        """
        Ignore the commands from a channel on a server. This means that nobody will be able to use commands in this channel.

        1) Same as member. If the channel is already ignored, then you can delete it by typing 'yes'.
        2) Else,if the channel has commands enabled, it disables them from now on and says every time someone tries to use a command that commands aren't available on this channel
        """
        channel = channel or ctx.channel
        is_channel_ignored = channel.id in self.ignored_channels
        if is_channel_ignored:
            await ctx.send("This channel is already ignored. Type 'yes' if you want people to be able to use commands there !")
            try: #Confirm
                confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
            except asyncio.TimeoutError:
                await ctx.send("You didn't answer fast enough. Aborting the process !")
            else:
                if confirm.content.lower() == "yes": #confirm 
                    await self.bot.db.execute("DELETE FROM ignored_channels WHERE channel_id = ?",(channel.id,))
                    await self.bot.db.commit()
                    self.ignored_channels.remove(channel.id)
                    await ctx.send(f"{channel.mention} now has enabled commands !")
                else:
                    await ctx.send("Aborting process !")
        else:
            await self.bot.db.execute("INSERT INTO ignored_channels VALUES(?);",(channel.id,))
            await self.bot.db.commit()
            self.ignored_channels.add(channel.id)
            await ctx.send(f"{channel.mention} now has disabled commands !")

    @commands.group(invoke_without_command=True,aliases=["clear"],help="Deletes the last X messages from the channel.")
    async def purge(self,ctx,amount:int=2): #Delete "Amount" messages from the current channel. $purge [int]
        """
        Deletes a certain amount of message from the channel the command is used in. This command can have more detailed purge options, with the subcommands.

        Usage example : $purge 10
        This will delete the last 10 messages from the channel.
        """
        await ctx.message.delete()
        if ctx.invoked_subcommand is None:
            purged_messages = await ctx.channel.purge(limit=int(amount))
            return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)

    @purge.command(help="A subcommand of `purge` function. Deletes ONLY commands in the last X messages.")
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
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:m.author.bot or m.content.startswith(guild_prefix))
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)

    @purge.command(help="Deletes every message from bots in the last X messages.")
    async def bots(selt,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : the message's author is a bot.
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:m.author.bot)
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)
    
    @purge.command(help="Deletes every message that were sent by us, humans, and that don't call a command.")
    async def humans(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : the message's author is NOT a bot AND the message doesn't call a command.
        """
        guild_prefix = tuple(await get_prefix(self.bot,ctx.message))
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:not (m.author.bot or m.content.startswith(guild_prefix)))
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)

    @purge.command(help="Deletes every message of a member in the last X messages.")
    async def member(self,ctx,amount:int=2,member:discord.Member=None):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : the message's author is NOT a bot.
        """
        member = member or ctx.author
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:m.author == member)
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)
    
    @purge.command()
    async def match(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : [content] is in the message.
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:content in m.content)
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)

    @purge.command(name="not",help="Deletes messages that DON'T contain `content` in it.")
    async def _not(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : [content] is NOT in the message.
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:not (content in m.content))
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)
    
    @purge.command(help="Pretty clear. Deletes messages that starts with `content`.")
    async def startswith(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : message starts with [content] .
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:m.content.startswith(content))
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)
    
    @purge.command(help="Pretty clear. Deletes messages that ends with `content`.")
    async def endswith(self,ctx,amount:int=2,*,content):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : message ends with [content].
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:m.content.endswith(content))
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)
        
    @purge.command(help="Deletes messages that contains embeds.")
    async def embeds(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.

        Conditions : message is an embed.
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:len(m.embeds))
        await ctx.message.delete()
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)

    @purge.command(aliases=["attach"],help="Deletes messages that have an attachment. NOT FULLY ACCURATE.")
    async def attachments(self,ctx,amount:int=2):
        """
        /!\ This doesn't delete exactly [amount] messages matching the conditions below. This iterates through the last [amount] textchannel's messages and deletes each message that matches the conditions.
        This one is not fully accurate 
        Conditions : message ends with [content].
        """
        purged_messages = await ctx.channel.purge(limit=amount,check=lambda m:len(m.attachments) or m.content.startswith(("https://cdn.discordapp.com/attachments/","https://tenor.com/view/")))
        await ctx.message.delete()
        return await ctx.send(f"Deleted : {len(purged_messages)} messages.",delete_after=10)

def setup(bot):
    bot.add_cog(Moderation(bot))