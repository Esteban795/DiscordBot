import discord
from discord.ext import commands
import aiosqlite

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

def setup(bot):
    bot.add_cog(CustomPrefixes(bot))