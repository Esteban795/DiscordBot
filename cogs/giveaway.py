import asyncio
from discord import message, role
from discord.ext import commands,tasks
import discord
import datetime
import random
from bot import TimeConverter

__all__ = ("GiveawayNotFound",)

class GiveawayNotFound(commands.CommandError):
    """A class that represents that a giveaway wasn't found in the database"""

class Giveaway(commands.Cog):

    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self._giveaway_loop.start()

    async def _giveaway_end_task(self,args):
        id,content,guild_id,channel_id,message_id,creator_id,end_time,done = args
        sleep_until = datetime.datetime.strptime(end_time,"%Y-%m-%d %H:%M:%S")
        await discord.utils.sleep_until(sleep_until)
        sql = "SELECT role_id FROM giveaways_roles WHERE id = ?"
        async with self.bot.db.execute(sql,(id,)) as cursor:
            roles_to_have = {i[0] for i in await cursor.fetchall()}
        try:
            message = discord.utils.get(self.bot.cached_messages,id=message_id)
            if message is None:
                raise AttributeError
        except AttributeError:
            channel = self.bot.get_channel(channel_id)
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                return await channel.send("Giveaway message not found. It was most likely deleted !")
        except Exception as e:
            channel = self.bot.get_channel(channel_id)
            return await channel.send(f"An unknow error occured. ({e})")

        def check(roles_ids):
            return any(x in roles_to_have for x in roles_ids)
        members_list = await message.reactions[0].users().flatten()
        if roles_to_have:
            actual_list = []
            for member in members_list:
                if member.bot:
                    continue
                roles_ids_list = [role.id for role in member.roles if not member.bot]
                if check(roles_ids_list):
                    actual_list.append(member)
        else:
            actual_list = [member for member in members_list if not member.bot]
        embed = discord.Embed(title=f"Giveaway `{content}` ended !",url=message.jump_url)
        l = len(actual_list)
        if not l:
            embed.description = "No one voted :("
        else:
            n = random.randint(0,len(actual_list) - 1)
            embed.description = f"\U0001f387 {actual_list[n].mention} is the winner. \U0001f387 \n \n \n {l} participants."
        await message.channel.send(embed=embed)
        await self.bot.db.execute("UPDATE giveaways SET done = 1 WHERE id = ?",(id,))
        await self.bot.db.commit()

    @tasks.loop(seconds=60)
    async def _giveaway_loop(self):
        await self.bot.wait_until_ready()
        sql = "SELECT * FROM giveaways WHERE done = 0 AND CAST((julianday(end_time) - julianday('now'))*86400 AS INTEGER) <= 60"
        async with self.bot.db.execute(sql) as cursor:
            async for row in cursor:
                await self._giveaway_end_task(row)
    
    async def _giveaway_exists(self,guild_id,content):
        async with self.bot.db.execute("SELECT * FROM giveaways WHERE content = ? AND done = 0",(content,)) as cursor:
            result = await cursor.fetchall()
        if result is None:
            raise GiveawayNotFound(f"No giveaway named `{content}` was found.")
        return result

    @commands.group(invoke_without_command=True,aliases=["giveaways"])
    async def giveaway(self,ctx):
        if ctx.invoked_subcommand is None:
            running_giveaways = []
            async with self.bot.db.execute("SELECT * FROM giveaways WHERE guild_id = ? AND done = 0",(ctx.guild.id,)) as cursor:
                async for row in cursor:
                    id,content,guild_id,channel_id,message_id,end_time,done = row
                    datetime_object = datetime.datetime.strptime(end_time,"%Y-%m-%d %H:%M:%S")
                    async with self.bot.db.execute("SELECT role_id  FROM giveaways_roles WHERE id = ?",(id,)) as cursor:
                        roles_ids = [ctx.guild.get_role(i[0]) for i in await cursor.fetchall()]
                    timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
                    if roles_ids:
                        fmt = " ".join([f"{role.mention}" for role in roles_ids])
                        running_giveaways.append(f"- `{content}` (ends <t:{timestamp}:f> , roles : {fmt}")
            if len(running_giveaways) == 0:
                return await ctx.send("No running giveaways !")
            embed = discord.Embed(title=f"Running giveaways for `{ctx.guild}` : ")
            embed.description = "\n".join(running_giveaways)
            return await ctx.send(embed=embed)
    
    @giveaway.command(aliases=["add","new"])
    async def create(self,ctx,time:TimeConverter,*,content):
        datetime_object = (datetime.datetime.utcnow() + datetime.timedelta(seconds=time))
        timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
        embed = discord.Embed(title=content,description=f"Ends : <t:{timestamp}:f>")
        giveaway = await ctx.send(embed=embed)
        await giveaway.add_reaction("\U0001f387")
        sql = "INSERT INTO giveaways(content,guild_id,channel_id,message_id,creator_id,end_time) VALUES (?,?,?,?,?,?)"
        await self.bot.db.execute(sql,(content,ctx.guild.id,ctx.channel.id,giveaway.id,ctx.author.id,datetime_object.replace(microsecond=0)))
        await self.bot.db.commit()

    @giveaway.command()
    async def remove(self,ctx,*,name):
        giveaway_exists = await self._giveaway_exists(ctx.guild.id,name)
        if not (ctx.author.guild_permissions.manage_guild or ctx.author.id == giveaway_exists[5]):
            return await ctx.send("Only giveaway creator or people that have the 'manage server' permission are allowed to stop the giveaway")
        try:
            await ctx.send(f"Are you sure you want to delete `{giveaway_exists[1]} ?")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute("DELETE FROM giveaways WHERE id = ?",(giveaway_exists[0],))
                await self.bot.db.execute("DELETE FROM giveaways_roles WHERE id = ?",(giveaway_exists[0],))
                await self.bot.db.commit()
                return await ctx.send(f"Deleted `{name}` giveaway.")
            return await ctx.send("Aborting process.")
    
    @giveaway.group(invoke_without_command=True)
    async def roles(self,ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send("Uhm. You need to use subcommands here.")
    
    @roles.command(aliases=["add","new"])
    async def create(self,ctx,time:TimeConverter,roles:commands.Greedy[discord.Role],*,content):
        datetime_object = (datetime.datetime.utcnow() + datetime.timedelta(seconds=time))
        timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
        embed = discord.Embed(title=content,description=f"Ends : <t:{timestamp}:f>")
        fmt = " ".join([f"{role.mention}" for role in roles])
        embed.add_field(name="Roles allowed :",value=fmt)
        giveaway = await ctx.send(embed=embed)
        await giveaway.add_reaction("\U0001f387")
        sql = "INSERT INTO giveaways(content,guild_id,channel_id,message_id,creator_id,end_time) VALUES (?,?,?,?,?,?)"
        new_id = await self.bot.db.execute_insert(sql,(content,ctx.guild.id,ctx.channel.id,giveaway.id,ctx.author.id,datetime_object.replace(microsecond=0)))
        for role in roles:
            await self.bot.db.execute("INSERT INTO giveaways_roles VALUES(?,?)",(new_id[0],role.id))
        await self.bot.db.commit()

def setup(bot):
    bot.add_cog(Giveaway(bot))