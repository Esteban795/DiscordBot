from discord.ext import commands
import async_google_trans_new
from bot import LANGUAGES

class Translator(commands.Cog):

    def __init__(self,bot,languages_available):
        self.bot = bot
        self.translator = async_google_trans_new.AsyncTranslator()
        self.languages_available = languages_available
    
    @commands.command()
    async def translate(self,ctx,target,*,text):
        r = await self.translator.translate(text,target)
        print(dir(r))
        return await ctx.send(r)


def setup(bot):
    bot.add_cog(Translator(bot,LANGUAGES))