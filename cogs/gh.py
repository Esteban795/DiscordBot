import discord
from discord.ext import commands
import aiohttp
import re
from datetime import datetime

class Github(commands.Cog):
    def __init__(self,bot) -> None:
        self.bot = bot
        self.MAX_LEN = 2000
    
    def _embed_builder(self,code,file_ext,repo_url):
        """
        Build the embed which is gonna be sent later.

        #### Parameters :
        - code : the piece of code that will be in the embed.
        - file_ext : the original file extension of the piece of code (used for markdown's code formatting)
        - repo_url : Github repository's URL.

        #### Returns : 
        - embed : a discord.Embed instance, filled with the infos we need.
        """
        embed = discord.Embed(title=f"Here is the code you asked me to get !",color=0x00ff00,timestamp=datetime.utcnow(),url=repo_url)
        embed.add_field(name="Code :",value=f"```{file_ext}\n{code}```" if len(code) <= 1023 else f"```{file_ext}\n{code[:900]}``` \n There is more, but I can't display it (more than 1024 characters)")
        return embed

    def valid_url(self,url):
        """
        Check if the url provided is a valid one.

        #### Parameters :
        - url : a Github file, stored in a repo, URL.

        ### Returns : 
        - is_valid : the URL and file extension, if valid. Else, returns None.
        """
        valid_url_regex = re.compile(r"(https:\/\/(?:www\.)?github\.com\/.{0,39}\/.{0,100}(?:\.(\w{1,4}))$)") #Check if the github url is a valid one.
        is_valid = valid_url_regex.findall(url)
        if is_valid:
            return is_valid
        else:
            return None

    def _url_converter(self,url:str)-> str:
        """
        Converts the already valid github file url.
        """
        return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    @commands.group(invoke_without_command=True,help="Shows the official repo for this bot.")
    async def github(self,ctx):
        """
        With no subcommands invoked, it sends an embed with the official repo url.
        """
        if ctx.invoked_subcommand is None:
            em = discord.Embed(title="Here is the official repository for this bot.",color=0x00ffff,timestamp=datetime.utcnow(),
            description="[Github repo](https://github.com/Esteban795/DiscordBot). Feel free to open any pull requests !")
            return await ctx.send(embed=em)

    @github.command(help="Allows you to display first lines of a code file, thanks to GitHub.")
    async def display(self,ctx,url:str):
        """
        Display the first lines of a GitHub code file.

        #### Parameters :
        - url : a github file url.

        ####  Returns :
        - an embed, with the code inside of it (markdown formatted.).
        - If url is not a valid one, returns a message that will tell it to you.
        """
        await ctx.message.edit(suppress=True) #Remove integrations
        is_valid = self.valid_url(url)
        if not is_valid:
            return await ctx.send("Link is invalid. Please provide a link like this one : `https://github.com/Esteban795/DiscordBot/blob/main/bot.py`")
        raw_content_url = self._url_converter(is_valid[0][0])
        file_extension = is_valid[0][1] 
        async with self.bot.cs.get(raw_content_url) as r:
            raw_code = await r.text()
        result = self._embed_builder(raw_code,file_extension,url)
        return await ctx.send(embed=result)

    @github.command(help="Lets you display from [start] to [end] lines of the GitHub code file.")
    async def lines(self,ctx,start:int,end:int,url:str):
        """
        Display from [start] to [end] lines from a GitHub code file.

        #### Parameters :
        - start : an integer. This will be the 'index' of the first line displayed in the embed.
        - end : an integer. This will be the 'index' of the last line displayed in the embed.
        - url : a github file url.

        ####  Returns :
        - an embed, with the code inside of it (markdown formatted.).
        - If url is not a valid one, returns a message that will tell it to you.
        """
        await ctx.message.edit(suppress=True)
        if start < 0 or end < 0:
            return await ctx.send("'Start' and 'End' parameter must be integers greater than 0.")
        if end < start:
            return await ctx.send("'End' parameter must be greater than 'Start' parameter.")
        is_valid = self.valid_url(url)
        if not is_valid:
            return await ctx.send("Link is invalid. Please provide a link like this one : `https://github.com/Esteban795/DiscordBot/blob/main/bot.py`")
        raw_content_url = self._url_converter(is_valid[0][0])
        file_extension = is_valid[0][1]
        async with self.bot.cs.get(raw_content_url) as r:
            raw_code = await r.text()
        lines = raw_code.splitlines()
        result = self._embed_builder("\n".join(lines[start-1:end]),file_extension,url)
        return await ctx.send(embed=result)

def setup(bot):
    bot.add_cog(Github(bot))
    