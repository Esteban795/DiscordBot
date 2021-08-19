import asyncio
from discord.ext import commands,tasks
import discord
import datetime
import random
from bot import TimeConverter

__all__ = ("GiveawayNotFound","Giveaway")

class GiveawayNotFound(commands.CommandError):
    """A class that represents that a giveaway wasn't found in the database"""

class Giveaway(commands.Cog):

    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self._giveaway_loop.start() #Starts the loop

    async def _giveaway_end_task(self,args):
        """
        Sleeps until the giveaway actually ends.
        Then, it tries to pick a winner, and sends it to the same channel that was used to start the giveaway. 
        """
        id,content,guild_id,channel_id,message_id,creator_id,end_time,done = args #Dispatch the args (got them from the db)
        sleep_until = datetime.datetime.strptime(end_time,"%Y-%m-%d %H:%M:%S") #Creates an actual datetime object, from the timestamp stored in db.
        await discord.utils.sleep_until(sleep_until)
        sql = "SELECT role_id FROM giveaways_roles WHERE id = ?" 
        async with self.bot.db.execute(sql,(id,)) as cursor: #id is the giveaway ID (unique). So the roles' id attached to this id are only for this giveaway.
            roles_to_have = {i[0] for i in await cursor.fetchall()}
        try:
            message = discord.utils.get(self.bot.cached_messages,id=message_id) #Tries to get the message from the bot's internal cache.
            if message is None: #Basically, message not found in the cache.
                raise AttributeError
        except AttributeError:
            channel = self.bot.get_channel(channel_id) #Channel where the giveaway command was used.
            try:
                message = await channel.fetch_message(message_id) #Tries to fetch the message
            except discord.NotFound:
                return await channel.send("Giveaway message not found. It was most likely deleted !") #Message somehow not found, most likely removed
        except Exception as e: #Idk what is happening here, I send it to the chat.
            channel = self.bot.get_channel(channel_id)
            return await channel.send(f"An unknow error occured. ({e})")

        def check(roles_ids): #Check if the member's roles' ids are in the allowed-to-participate roles.
            return any(x in roles_to_have for x in roles_ids)

        members_list = await message.reactions[0].users().flatten() #Gets every user that reacted to the bot's giveaway embed.
        if roles_to_have: #Do we have allowed-to-participate roles ?
            actual_list = []
            for member in members_list:
                if member.bot:
                    continue
                roles_ids_list = [role.id for role in member.roles] #Member's roles' ids
                if check(roles_ids_list):
                    actual_list.append(member)
        else: #No we don't, so anyone that is NOT a bot is gonna be in the actual list.
            actual_list = [member for member in members_list if not member.bot]
        embed = discord.Embed(title=f"Giveaway `{content}` ended !",url=message.jump_url)
        l = len(actual_list)
        if not l:
            embed.description = "No one voted :("
        else:
            n = random.randint(0,len(actual_list) - 1) #Random number.
            embed.description = f"\U0001f387 {actual_list[n].mention} is the winner. \U0001f387 \n \n \n {l} participants."
        await message.channel.send(embed=embed)
        await self.bot.db.execute("UPDATE giveaways SET done = 1 WHERE id = ?",(id,))
        await self.bot.db.commit()

    @tasks.loop(seconds=60)
    async def _giveaway_loop(self):
        await self.bot.wait_until_ready()
        sql = "SELECT * FROM giveaways WHERE done = 0 AND CAST((julianday(end_time) - julianday('now'))*86400 AS INTEGER) <= 60" #A giveaway that ends within 60 seconds.
        async with self.bot.db.execute(sql) as cursor:
            async for row in cursor:
                await self._giveaway_end_task(row) #We start a task for each giveaway that ends within 60 seconds.
    
    async def _giveaway_exists(self,guild_id,content):
        """Check if the giveaway exists. If it does, returns the row. Else, raises an error, handled in cogs/eh.py"""
        async with self.bot.db.execute("SELECT * FROM giveaways WHERE content = ? AND done = 0",(content,)) as cursor:
            result = await cursor.fetchall()
        if result is None:
            raise GiveawayNotFound(f"No giveaway named `{content}` was found.")
        return result

    @commands.group(invoke_without_command=True,aliases=["giveaways"],help="Without subcommands, get the running giveaways of this guild.")
    async def giveaway(self,ctx):
        """Returns the running giveaways from the guild."""
        if ctx.invoked_subcommand is None:
            running_giveaways = []
            async with self.bot.db.execute("SELECT id,content,end_time FROM giveaways WHERE guild_id = ? AND done = 0",(ctx.guild.id,)) as cursor:
                async for row in cursor:
                    id,content,end_time = row
                    datetime_object = datetime.datetime.strptime(end_time,"%Y-%m-%d %H:%M:%S")
                    async with self.bot.db.execute("SELECT role_id  FROM giveaways_roles WHERE id = ?",(id,)) as cursor:
                        roles_ids = [ctx.guild.get_role(i[0]) for i in await cursor.fetchall()]
                    timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
                    if roles_ids:
                        fmt = " ".join([f"{role.mention}" for role in roles_ids])
                        running_giveaways.append(f"- `{content}` (ends <t:{timestamp}:f> , roles : {fmt})")
                    else:
                        running_giveaways.append(f"- `{content}` (ends <t:{timestamp}:f>)")
            if len(running_giveaways) == 0:
                return await ctx.send("No running giveaways !")
            embed = discord.Embed(title=f"Running giveaways for `{ctx.guild}` : ")
            embed.description = "\n".join(running_giveaways)
            return await ctx.send(embed=embed)
    
    @giveaway.command(aliases=["add","new"],help="Creates a new giveaway. Specify the time using units like 1h,2d,2m (similar to how ban command does it.")
    async def create(self,ctx,time:TimeConverter,*,content):
        """
        Creates a new giveaway.

        #### Parameters : 
        - time : a string made of an integer or a float, followed by a letter (mshd). See how `TimeConverter` works to know more.
        - content : this can be almost anything. This is like a title, a description to explain the giveaway.
        """
        datetime_object = (datetime.datetime.utcnow() + datetime.timedelta(seconds=time)) #Get the end time for this giveaway.
        timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds()) #Transforms it as a UNIX timestamp, to allow Discord to render it properly.
        embed = discord.Embed(title=content,description=f"Ends : <t:{timestamp}:f>")
        giveaway = await ctx.send(embed=embed) 
        await giveaway.add_reaction("\U0001f387")
        sql = "INSERT INTO giveaways(content,guild_id,channel_id,message_id,creator_id,end_time) VALUES (?,?,?,?,?,?)"
        await self.bot.db.execute(sql,(content,ctx.guild.id,ctx.channel.id,giveaway.id,ctx.author.id,datetime_object.replace(microsecond=0))) #Add the giveaway to the db.
        await self.bot.db.commit()

    @giveaway.command(aliases=["delete"],help="Lets you delete a running giveaway. If no giveaway found, use `$giveaway` to see the running giveaways.")
    async def remove(self,ctx,*,name):
        """Delete a giveaway
        
        #### Parameters : 
        - name : the giveaway name.

        #### Returns :
        - Giveaway successfully deleted, or 'errors', means you're not allowed to do some stuff.
        - GiveawayNotFound : giveaway named `name` doesn't exist.
        """
        giveaway_exists = await self._giveaway_exists(ctx.guild.id,name) #Does the giveaway exist
        if not (ctx.author.guild_permissions.manage_guild or ctx.author.id == giveaway_exists[5]): #Possible bypass if you have manage server permissions.
            return await ctx.send("Only giveaway creator or people that have the 'manage server' permission are allowed to stop the giveaway")
        try:
            await ctx.send(f"Are you sure you want to delete `{giveaway_exists[1]} ?")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15) #Confirm you want to delete it.
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower() == "yes": #wants to delete it.
                await self.bot.db.execute("DELETE FROM giveaways WHERE id = ?",(giveaway_exists[0],)) #giveaway_exists[0] is the ID of the giveaway
                await self.bot.db.execute("DELETE FROM giveaways_roles WHERE id = ?",(giveaway_exists[0],))
                await self.bot.db.commit()
                return await ctx.send(f"Deleted `{name}` giveaway.")
            return await ctx.send("Aborting process.")
    
    @giveaway.group(invoke_without_command=True,help="This is a subcommand to let you create a roles-only giveaway. You need to use the `create` subcommand to actually create a giveaway.")
    async def roles(self,ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send("Uhm. You need to use subcommands here.")
    
    @roles.command(aliases=["add","new"])
    async def create(self,ctx,time:TimeConverter,roles:commands.Greedy[discord.Role],*,content):
        datetime_object = (datetime.datetime.utcnow() + datetime.timedelta(seconds=time)) #Same as previous create function.
        timestamp = int((datetime_object - datetime.datetime(1970,1,1)).total_seconds())
        embed = discord.Embed(title=content,description=f"Ends : <t:{timestamp}:f>")
        fmt = " ".join([f"{role.mention}" for role in roles])
        embed.add_field(name="Roles allowed :",value=fmt) #Roles allowed.
        giveaway = await ctx.send(embed=embed)
        await giveaway.add_reaction("\U0001f387")
        sql = "INSERT INTO giveaways(content,guild_id,channel_id,message_id,creator_id,end_time) VALUES (?,?,?,?,?,?)" #Insert the giveaway in the db.
        new_id = await self.bot.db.execute_insert(sql,(content,ctx.guild.id,ctx.channel.id,giveaway.id,ctx.author.id,datetime_object.replace(microsecond=0)))
        for role in roles: #Insert the roles with the corresponding giveaway ID.
            await self.bot.db.execute("INSERT INTO giveaways_roles VALUES(?,?)",(new_id[0],role.id))
        await self.bot.db.commit()

def setup(bot):
    bot.add_cog(Giveaway(bot))