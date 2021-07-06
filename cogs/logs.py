import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime
class Logs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    async def get_logs_channels(self,guild_id):
        """
        Retrieves the log channel ID for the guild.
        
        ### Parameters :
        - guild_id : an integer, supposed to represent the ID of a discord.Guild object.

        ### Raises : 
        - Nothing.

        ### Returns :
        - The log channel ID if there is one in the database, else None.
        """
        async with aiosqlite.connect("databases/main.db") as db:
            cursor = await db.execute("SELECT channel_id FROM logs_channels WHERE guild_id = (?);",(guild_id,))
            result = await cursor.fetchone()
        if result:
            return result[0]
        return None

    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        """When the bot leaves a guild, we don't need to send a log message no more.So we just delete the log channel from the database."""
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("DELETE FROM logs_channels WHERE guild_id = (?);",(guild.id,))
            await db.commit()

    @commands.group(invoke_without_command=True,aliases=["log"])
    async def logs(self,ctx):
        """Does nothing without a subcommand."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Subcommand required.")
    
    @logs.group()
    async def logchannel(self,ctx):
        """Does nothing without a subcommand"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Either add, edit or remove a log channel.")
    
    @logchannel.command()
    async def add(self,ctx,text_channel:discord.TextChannel=None):
        text_channel = text_channel or ctx.channel
        """Adds the ID of either the specified channel or the channel the command was called in.
        
        ### Parameters : 
        - text_channel [Optional] : the text channel where log message will be sent in the future.

        ### Returns :
        - A message that confirms you your channel was correctly added to the database.
        """
        await text_channel.send(f"{ctx.author} picked this channel to be the log channel. I will send everything I can track here (kick, ban, messages deleted,reactions added etc..).")
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("INSERT INTO logs_channels VALUES(?,?);",(ctx.guild.id,text_channel.id))
            await db.commit()
    
    @logchannel.command()
    async def remove(self,ctx):
        """Removes the log channel ID from the database. This means no log message will be sent after this command."""
        await ctx.send(f"{ctx.author} decided to disable the logs in this server. You can always re-add it back later !")
        async with aiosqlite.connect("databases/main.db") as db:
            await db.execute("DELETE FROM logs_channels WHERE guild_id = (?);",(ctx.guild.id,))
            await db.commit()
    
    @commands.Cog.listener()
    async def on_message(self,message):
        """On_message event to help us log everything.
        
        ### Parameters : 
        - message : discord.Message object. This is automatically provided by the API, so no user input.

        ### Returns :
        - Send a log message with the content of the message into the log channel predefined by a command.
        """
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
            original_channel = self.bot.get_channel(payload.channel_id)
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

def setup(bot):
    bot.add_cog(Logs(bot))