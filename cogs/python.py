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

    @commands.command(name="exec")
    async def _exec(self,ctx, *, code):
        str_obj = io.StringIO() 
        try:
            with contextlib.redirect_stdout(str_obj) as f:
                exec(code)
            output = f.getvalue()
            s = output if len(output) > 0 else "No output !"
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
            embed = discord.Embed(title="Your code executed without any problem.",color=0xaaffaa,timestamp=datetime.utcnow(),description=f"```{s}```")
            return await ctx.send(embed=embed)
        embed = discord.Embed(title="Your code wasn't executed correctly.",color=0xffaaaa,timestamp=datetime.utcnow(),description=f"```Command raised an exception : \n {error_class} at line {line_number} of source string : {detail}```")
        return await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Python(bot))