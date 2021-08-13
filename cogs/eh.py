from discord.ext import commands
from difflib import get_close_matches
from cogs.music import *
from cogs.giveaway import *

class ErrorHandler(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self,ctx, error):
        """
        A basic command error handler for our bot. Most of the time, it will return the error message to the channel.

        ### Parameters :
        - None to be given by user. error is an error type.

        ### Raises : 
        - Error gets sent into ctx.channel.

        ### Returns : 
        - The error message.
        """
        if isinstance(error, commands.CommandNotFound):
            """Command doesn't exist"""
            cmd = ctx.invoked_with #the command name
            cmds = [cmd.name for cmd in self.bot.commands] #Get all commands registered in the bot
            matches = "\n".join(get_close_matches(cmd, cmds,n=3)) #Get the three closest matches from the command name
            if len(matches) > 0:
                return await ctx.send(f"Command \"{cmd}\" not found. Maybe you meant :\n{matches}") #close enough match from the wrong command name
            else:
                return await ctx.send(f'Command "{cmd}" not found, use the help command to know what commands are available') #No match
        elif isinstance(error,commands.MissingPermissions):
            return await ctx.send(error)
        elif isinstance(error,commands.MissingRequiredArgument):
            return await ctx.send(error)
        elif isinstance(error,commands.NotOwner):
            await ctx.send("You must be the owner of this bot to perform this command. Please contact Esteban#7985 for more informations.")
        elif isinstance(error,commands.BadArgument):
            print(error)
            await ctx.send(error)
        elif isinstance(error,commands.DisabledCommand):
            await ctx.send(error)
        elif isinstance(error,commands.NoPrivateMessage):
            await ctx.send(error)
        elif isinstance(error,commands.CheckFailure):
            await ctx.send(error,allowed_mentions=self.bot.allowed_mentions)
        elif isinstance(error,NoVoiceClient):
            await ctx.send(error)
        elif isinstance(error,NotSameVoiceChannel):
            await ctx.send(error)
        elif isinstance(error,AuthorIsNotInVoiceChannel):
            await ctx.send(error)
        elif isinstance(error,PlaylistNotFound):
            await ctx.send(error)
        elif isinstance(error,InvalidSlice):
            await ctx.send(error)
        elif isinstance(error,InvalidPlaylistLink):
            await ctx.send(error)
        elif isinstance(error,GiveawayNotFound):
            await ctx.send(error)
        else:
            raise error

def setup(bot):
    bot.add_cog(ErrorHandler(bot))