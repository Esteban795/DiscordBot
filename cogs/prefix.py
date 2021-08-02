from discord.ext import commands

class CustomPrefixes(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        await self.bot.db.execute("DELETE FROM prefixes WHERE guild_id = ?",(guild.id,))
        await self.bot.db.commit()
    
    @commands.group()
    async def prefix(self,ctx):
        if ctx.invoked_subcommand is None:
            cursor = await self.bot.db.execute("SELECT prefix FROM prefixes WHERE guild_id = ?",(ctx.guild.id,))
            result = await cursor.fetchall()
            if result:
                await ctx.send(f"Custom prefixes for {ctx.guild} : {' '.join([i[0] for i in result])}")
            else:
                await ctx.send("No custom prefixes defined.")

    @prefix.command()
    async def add(self,ctx,*custom_prefixes):
        for prefix in custom_prefixes:
            await self.bot.db.execute("INSERT OR IGNORE INTO prefixes VALUES(?,?)",(ctx.guild.id,prefix))
        await self.bot.db.commit()
        await self.prefix(ctx)

    @prefix.command()
    async def remove(self,ctx):
        await self.bot.db.execute("DELETE FROM prefixes WHERE guild_id = ?;",(ctx.guild.id,))
        await self.bot.db.commit()
        await ctx.send("Custom prefixes were removed. You now have to use my default prefix, which is '$'.")
    
    @prefix.command()
    async def edit(self,ctx,*custom_prefixes):
        await self.bot.db.execute("DELETE FROM prefixes WHERE guild_id = ?",(ctx.guild.id,))
        for prefix in custom_prefixes:
            await self.bot.db.execute("INSERT INTO prefixes VALUES(?,?);",(ctx.guild.id,prefix))
        await self.bot.db.commit()
        await ctx.send(f"Custom prefixes : {' '.join(custom_prefixes)}")

def setup(bot):
    bot.add_cog(CustomPrefixes(bot))