import discord
from discord.ext import commands
import aiosqlite

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

def setup(bot):
    bot.add_cog(CustomOnMessage(bot))