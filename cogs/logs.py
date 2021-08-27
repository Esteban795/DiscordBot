import asyncio
from operator import add
from os import name
from discord.ext import commands
import discord
from datetime import datetime


__all__ = ("LogChannelNotFound","IgnoredLogChannelNotFound")

class LogChannelNotFound(commands.CommandError):
    """A class that represents the fact that a log channel hasn't been set up."""

class IgnoredLogChannelNotFound(commands.CommandError):
    """A class that represents the fact that a log channel hasn't been set up."""

class Logs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.bot.loop.create_task(self._load_logschannels())
        self._logschannels = {}
        self.emojis = {True:"\U00002705",False:"\U0000274c",None:"\U000025ab"}

    def _format_overwrites(self,d:dict):
        return "\n".join([f"{target.mention} : \n" + "\n".join([f"- {permission[0]} : {permission[1]}" for permission in overwrites if permission[1] is not None]) for target,overwrites in d.items()])

    async def _load_logschannels(self):
        await self.bot.wait_until_ready()
        async with self.bot.db.execute("SELECT * FROM logs_channels") as cursor:
            async for row in cursor:
                self._logschannels[row[1]] = row[0]

    def _get_guild_logchannel(self,guild_id):
        try:
            channel_id = self._logschannels[guild_id]
        except KeyError: #Channel doesn't exist
            raise LogChannelNotFound("Your server has no logs channel.")
        else:
            return channel_id

    def _log_channel_exists(self,guild_id):
        try:
            channel_id = self._logschannels[guild_id]
        except KeyError: #Channel doesn't exist
            raise IgnoredLogChannelNotFound("Log channel not found.")
        else:
            return channel_id

    @commands.group(invoke_without_command=True)
    async def logchannel(self,ctx):
        if ctx.invoked_subcommand is None:
            channel_id = self._get_guild_logchannel(ctx.guild.id)
            channel = ctx.guild.get_channel(channel_id) or await ctx.guild.fetch_channel(channel_id)
            return await ctx.send(f"{channel.mention} is your current logs channel.")
    
    @logchannel.command(name="set")
    async def _set(self,ctx,channel : discord.TextChannel):
        await self.bot.db.execute("UPDATE logs_channels SET channel_id = ? WHERE guild_id = ?",(channel.id,ctx.guild.id))
        await self.bot.db.commit()
        self._logschannels[ctx.guild.id] = channel.id
        return await ctx.send(f"{channel.mention} is the new logs channel.")

    @logchannel.command()
    async def remove(self,ctx):
        try:
            await ctx.send("Are you sure you want to remove the logs channel from this servers ?")
            confirm = await self.bot.wait_for("message",check= lambda m : m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower():
                await self.bot.db.execute("DELETE FROM logs_channels WHERE guild_id = ?",(ctx.guild.id,))
                await self.bot.db.commit()
                del self._logschannels[ctx.guild.id]
                return await ctx.send(f"Logs channel removed.")
            return await ctx.send("Aborting process.")

    @commands.Cog.listener()
    async def on_message_delete(self,message : discord.Message):
        if message.author.bot:
            return
        log_channel_id = self._log_channel_exists(message.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Message deleted.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.add_field(name="Message content :",value=message.content)
        embed.add_field(name="Author :",value=message.author.mention)
        embed.add_field(name="Original channel :",value=message.channel.mention)
        return await log_channel.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self,payload):
        log_channel_id = self._log_channel_exists(payload.guild_id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title=f"{len(payload.message_ids)} messages deleted.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.add_field(name="Channel :",value=self.bot.get_channel(payload.channel_id).mention)
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self,before,after):
        log_channel_id = self._log_channel_exists(before.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Message edited.",color=0xffaaaa,url=after.jump_url,timestamp=datetime.utcnow())
        if before.content != after.content:
            embed.description = "Content edited."
            embed.add_field(name="Old content :",value=before.content)
            embed.add_field(name="New content :",value=after.content)
            embed.set_author(name=before.author,icon_url=before.author.avatar_url)
        elif before.pinned != after.pinned:
            if before.pinned:
                embed.description = "Message unpinned."
            else:
                embed.description = "Message pinned."
        elif before.embeds != after.embeds:
            embed.description = "Embeds changed."
        return await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        log_channel_id = self._log_channel_exists(payload.guild_id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Reaction added.",color=0xffaaaa,url=f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}",timestamp=datetime.utcnow())
        member = self.bot.get_user(payload.user_id)
        embed.add_field(name="Member who reacted :",value=member.mention)
        if payload.emoji.is_custom_emoji():
            if payload.emoji.animated:
                emoji = f"<a:{payload.emoji.name}:{payload.emoji.id}>"
            else:
                emoji = f"<:{payload.emoji.name}:{payload.emoji.id}>"
        else:
            emoji = payload.emoji.name
        embed.add_field(name="Emoji :",value=emoji)
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self,payload):
        log_channel_id = self._log_channel_exists(payload.guild_id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Reaction removed.",color=0xffaaaa,url=f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}",timestamp=datetime.utcnow())
        member = self.bot.get_user(payload.user_id)
        embed.add_field(name="Member who removed their reaction :",value=member.mention)
        if payload.emoji.is_custom_emoji():
            if payload.emoji.animated:
                emoji = f"<a:{payload.emoji.name}:{payload.emoji.id}>"
            else:
                emoji = f"<:{payload.emoji.name}:{payload.emoji.id}>"
        else:
            emoji = payload.emoji.name
        embed.add_field(name="Emoji :",value=emoji)
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self,payload):
        log_channel_id = self._log_channel_exists(payload.guild_id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Reactions cleared.",color=0xffaaaa,url=f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}",timestamp=datetime.utcnow())
        return await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self,channel : discord.abc.GuildChannel):
        muted_role = discord.utils.get(channel.guild.roles,name="Muted") or discord.utils.get(channel.guild.roles,name="muted")
        await channel.set_permissions(muted_role,send_messages=False,speak=False,add_reactions=False)
        log_channel_id = self._log_channel_exists(channel.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Channel created.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.add_field(name="Channel :",value=channel.mention)
        fmt_overwrites = "\n\n".join([f"- `{target}` :\n" + "\n".join([f"{perm[0]} : {perm[1]}" for perm in permissions if perm[1] is not None]) for target,permissions in channel.overwrites.items()])
        embed.add_field(name="Current overwrites : ",value=fmt_overwrites,inline=False)
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self,channel):
        log_channel_id = self._log_channel_exists(channel.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        if log_channel == channel:
            del self._logschannels[channel.guild.id]
            await self.bot.db.execute("DELETE FROM logs_channels WHERE guild_id = ?",(channel.guild.id,))
            return await self.bot.db.commit()
        embed = discord.Embed(title="Channel deleted.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.add_field(name="Channel :",value=channel.name)
        return await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self,before,after):
        log_channel_id = self._log_channel_exists(before.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(color=0xffaaaa,timestamp=datetime.utcnow())
        embed.description = f"Channel : {after.mention}"
        c = 0
        if before.name != after.name:
            c += 1
            embed.add_field(name="Old name : ",value=before.name)
            embed.add_field(name="New name  :",value=after.mention)
        if before.overwrites != after.overwrites:
            c += 1
            added_overwrites = {}
            removed_overwrites = {}
            edited_overwrites = {}
            before_not_after = set(before.overwrites).difference(after.overwrites)
            after_not_before = set(after.overwrites).difference(before.overwrites)
            if len(before_not_after):
                for target in before_not_after:
                    removed_overwrites[target] = before.overwrites[target]
                embed.add_field(name="Removed overwrites :",value=self._format_overwrites(removed_overwrites))
            elif len(after_not_before):
                for target in after_not_before:
                    added_overwrites[target] = after.overwrites[target]
                if len(added_overwrites):
                    embed.add_field(name="Added overwrites :",value=self._format_overwrites(added_overwrites))
            else:
                for target in before.overwrites:
                    if target in before_not_after or target in after_not_before:
                        continue
                    before_overwrites = [overwrites for overwrites in before.overwrites[target]]
                    after_overwrites = [overwrites for overwrites in after.overwrites[target]]
                    after_overwrites_not_before = set(after_overwrites).difference(before_overwrites)
                    if len(after_overwrites_not_before) == 0:
                        continue
                    edited_overwrites[target] = after_overwrites_not_before
                if len(edited_overwrites):
                    embed.add_field(name="Edited overwrites :",value=self._format_overwrites(edited_overwrites))
        if isinstance(before,discord.TextChannel):
            if before.topic != after.topic:
                c += 1
                embed.add_field(name="Old topic : ",value=before.topic)
                embed.add_field(name="New topic  :",value=after.topic)
            if before.position != after.position:
                c += 1
                embed.add_field(name="Old position : ",value=before.topic)
                embed.add_field(name="New position :",value=after.topic)
            if before.slowmode_delay != after.slowmode_delay:
                c += 1
                embed.add_field(name="Old slowmode delay : ",value=before.slowmode_delay)
                embed.add_field(name="New slowmode delay :",value=after.slowmode_delay)
        elif isinstance(before,discord.VoiceChannel):
            if before.user_limit != after.user_limit:
                c += 1
                embed.add_field(name="Old users limit :",value=before.user_limit)
                embed.add_field(name="New users limit :",value=after.user_limit)
            if before.rtc_region != after.rtc_region:
                c += 1
                embed.add_field(name="Old voice channel region :",value=before.rtc_region)
                embed.add_field(name="New voice channel region :",value=after.rtc_region)
            if before.bitrate != after.bitrate:
                c += 1
                embed.add_field(name="Old bitrate :",value=f"{str(before.bitrate/1000)}kbps")
                embed.add_field(name="New bitrate :",value=f"{str(after.bitrate/1000)}kbps") 
        if c == 1:
            embed.title = "1 change."
        else:
            embed.title = f"{c} changes."   
        return await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self,member):
        log_channel_id = self._log_channel_exists(member.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title=f"{member.mention} just joined.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.set_author(name=member,icon_url=member.avatar_url)
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        log_channel_id = self._log_channel_exists(member.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title=f"{member.mention} just left the server.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.set_author(name=member,icon_url=member.avatar_url)
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self,before,after):
        log_channel_id = self._log_channel_exists(before.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Member updated.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.set_author(name=after,icon_url=after.avatar_url)
        if before.display_name != after.display_name:
            embed.add_field(name="Old nickname :",value=before.display_name)
            embed.add_field(name="New nickname :",value=after.display_name)
        if before.roles != after.roles:
            before_not_after = set(before.roles).difference(after.roles)
            if len(before_not_after):
                embed.add_field(name="Removed roles :",value=", ".join([role.mention for role in before_not_after]))
            after_not_before = set(after.roles).difference(before.roles)
            if len(after_not_before):
                embed.add_field(name="New roles :",value=", ".join([role.mention for role in after_not_before]))
        if len(embed.fields) == 0:
            return
        return await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self,role):
        log_channel_id = self._log_channel_exists(role.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Role created.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.description = f"{role.mention} was created."
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self,role):
        log_channel_id = self._log_channel_exists(role.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Role deleted.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.description = f"{role.mention} was deleted."
        return await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self,before,after):
        log_channel_id = self._log_channel_exists(before.guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Role updated.",color=0xffaaaa,timestamp=datetime.utcnow())
        c = 0
        if before.name != after.name:
            c += 1
            embed.add_field(name="Old name :",value=before.name)
            embed.add_field(name="New name :",value=after.name)
        if before.permissions != after.permissions:
            c += 1
            before_not_after = set(before.permissions).difference(after.permissions)
            after_not_before = set(after.permissions).difference(before.permissions)
            if len(before_not_after):
                embed.add_field(name="Removed permissions :",value="\n".join([f"{permission} : {self.emojis[value]}" for permission,value in before_not_after]))
            if len(after_not_before):
                embed.add_field(name="New permissions :",value="\n".join([f"{permission} : {self.emojis[value]}" for permission,value in before_not_after]))
        if before.colour != after.colour:
            embed.color = after.color
            embed.description = "New color, see the embed color on the left !"
        return await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_ban(self,guild,user):
        log_channel_id = self._log_channel_exists(guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Member banned.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.set_author(name=user.mention,icon_url=user.avatar_url)
        msg = await log_channel.send(embed=embed)
        await asyncio.sleep(10)
        while True:
            ban = await guild.audit_logs(limit=1,action=discord.AuditLogAction.ban).flatten()
            if ban[0].target == user:
                break
        embed.add_field(name="Banned by :",value=ban[0].user)
        embed.add_field(name="Reason :",value=ban[0].reason)
        return await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self,guild,user):
        log_channel_id = self._log_channel_exists(guild.id)
        log_channel = self.bot.get_channel(log_channel_id)
        embed = discord.Embed(title="Member unbanned.",color=0xffaaaa,timestamp=datetime.utcnow())
        embed.set_author(name=user.mention,icon_url=user.avatar_url)
        msg = await log_channel.send(embed=embed)
        await asyncio.sleep(10)
        while True:
            ban = await guild.audit_logs(limit=1,action=discord.AuditLogAction.unban).flatten()
            if ban[0].target == user:
                break
        embed.add_field(name="Banned by :",value=ban[0].user)
        embed.add_field(name="Reason :",value=ban[0].reason)
        return await msg.edit(embed=embed)

def setup(bot):
    bot.add_cog(Logs(bot))