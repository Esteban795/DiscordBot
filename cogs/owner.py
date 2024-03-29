import discord
from discord.ext import commands

class OwnerOnly(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        if ctx.author.id != 475332124711321611:
            raise commands.NotOwner("You must be owner to use any commands of the OwnerOnly cog.")
        return True
        
    @commands.command()
    async def spam(self,ctx,member:discord.Member=None):
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
    
    @commands.group(invoke_without_command=True)
    async def cogs(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(", ".join(self.bot.cogs.keys()))
    
    @cogs.command()
    async def load(self,ctx,*cogs):
        for cog in cogs:
            if cog == "owner":
                return await ctx.send("'Owner' cog cannot be turned off.")
            try:
                self.bot.load_extension(f"cogs.{cog}")
            except:
                return await ctx.send(f"Couldn't load : {cog}. Maybe it doesn't exist ?")
            else:
                await ctx.send(f"Succesfully loaded {cog}.")

    @cogs.command()
    async def unload(self,ctx,*cogs):
        for cog in cogs:
            if cog == "owner":
                return await ctx.send("'Owner' cog cannot be turned off.")
            try:
                self.bot.unload_extension(f"cogs.{cog}")
            except:
                return await ctx.send(f"Couldn't unload : {cog}. Maybe it doesn't exist ?")
            else:
                await ctx.send(f"Succesfully unloaded {cog}.")
        
    @cogs.command()
    async def reload(self,ctx,*cogs):
        for cog in cogs:
            if cog == "owner":
                return await ctx.send("'Owner' cog cannot be turned off.")
            try:
                self.bot.reload_extension(f"cogs.{cog}")
            except:
                return await ctx.send(f"Couldn't reload : {cog}. Maybe it doesn't exist ?")
            else:
                await ctx.send(f"Succesfully reloaded {cog}.")
            
    @commands.command()
    async def guildbyid(self,ctx,id:int):
        guild = self.bot.get_guild(id)
        await ctx.send(guild)

    @commands.command()
    async def userbyid(self,ctx,id:int):
        user = await self.bot.fetch_user(id)
        await ctx.send(user)
        
def setup(bot):
    bot.add_cog(OwnerOnly(bot))