import discord
from discord.ext import commands
import contextlib
import io
from datetime import datetime
import traceback
import sys

class Python(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    def cog_check(self,ctx):
        if ctx.author.id != 475332124711321611:
            raise commands.NotOwner("You must be owner to use any commands of the OwnerOnly cog.")
        return True

    @commands.command()
    async def eval(self,ctx, *, code):
        str_obj = io.StringIO() 
        try:
            with contextlib.redirect_stdout(str_obj) as f:
                exec(code)
            output = f.getvalue()
        except SyntaxError as err:
            error_class = err.__class__.__name__
            detail = err.args[0]
            line_number = err.lineno
        except Exception as err:
            error_class = err.__class__.__name__
            detail = err.args[0]
            cl, exc, tb = sys.exc_info()
            line_number = traceback.extract_tb(tb)[-1][1]
        else:
            return
        raise Exception(f"```Command raised an exception : \n {error_class} at line {line_number} of source string : {detail}```")

def setup(bot):
    bot.add_cog(Python(bot))