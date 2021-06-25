from discord.ext import commands
from difflib import get_close_matches

class ErrorHandler(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self,ctx, error):
        if isinstance(error, commands.CommandNotFound):
            cmd = ctx.invoked_with #the command name
            cmds = [cmd.name for cmd in self.bot.commands] #Get all commands registered in the bot
            matches = "\n".join(get_close_matches(cmd, cmds,n=3)) #Get the three closest matches from the command name
            if len(matches) > 0:
                return await ctx.send(f"Command \"{cmd}\" not found. Maybe you meant :\n{matches}")
            else:
                return await ctx.send(f'Command "{cmd}" not found, use the help command to know what commands are available') #No match
        elif isinstance(error,commands.MissingPermissions):
            return await ctx.send(error)
        elif isinstance(error,commands.MissingRequiredArgument):
            return await ctx.send(error)
        elif isinstance(error,commands.NotOwner):
            await ctx.send("You must be the owner of this bot to perform this command. Please contact Esteban#7985 for more informations.")
        elif isinstance(error,commands.BadArgument):
            await ctx.send(error)
        elif isinstance(error,commands.DisabledCommand):
            await ctx.send(error)
        elif isinstance(error,commands.NoPrivateMessage):
            await ctx.send(error)
        elif isinstance(error,commands.CommandError):
            await ctx.send(error)
        else:
            raise error

def setup(bot):
    bot.add_cog(ErrorHandler(bot))