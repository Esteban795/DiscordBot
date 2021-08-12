from discord.ext import commands,tasks
import discord

class Giveaway(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
    
    @tasks.loop()
    async def _giveaway_loop(self):
        pass