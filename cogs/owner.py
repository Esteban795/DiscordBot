import discord
from discord.ext import commands

class OwnerOnly(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def spam(ctx,member:discord.Member=None):
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
    
    @commands.command()
    async def cogs(self,ctx):
        await ctx.send(", ".join(self.bot.cogs.keys()))
    
    @commands.command()
    async def guildbyid(self,ctx,id:int):
        guild = self.bot.get_guild(id)
        await ctx.send(guild)

def setup(bot):
    bot.add_cog(OwnerOnly(bot))