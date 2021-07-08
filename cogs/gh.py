import discord
from discord.ext import commands
import aiohttp
import re
from datetime import datetime

class Github(commands.Cog):
    def __init__(self,bot) -> None:
        self.bot = bot
        self.MAX_LEN = 2000
        self.session = aiohttp.ClientSession()
    
    def embed_builder(self,code,file_ext):
        embed = discord.Embed(title="Here is the code you asked me to get !",color=0x00ff00,timestamp=datetime.utcnow())
        embed.add_field(name="Code :",value=f"```{file_ext}\n{code}```" if len(code) <= 1023 else f"```{file_ext}\n{code[:900]}``` \n There is more, but I can't display it (more than 1024 characters)")
        return embed

    def valid_url(self,url):
        valid_url_regex = re.compile(r"(https:\/\/(?:www\.)?github\.com\/.{0,39}\/.{0,100}(?:\.(\w{1,4}))$)")
        is_valid = valid_url_regex.findall(url)
        if is_valid:
            return is_valid
        else:
            return None

    def url_converter(self,url:str)-> str:
        print(url)
        return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    @commands.group(invoke_without_command=True)
    async def github(self,ctx):
        if ctx.invoked_subcommand is None:
            em = discord.Embed(title="Here is the official repository for this bot.",color=0x00ffff,timestamp=datetime.utcnow(),
            description="[Github repo](https://github.com/Esteban795/DiscordBot). Feel free to open any pull requests !")
            return await ctx.send(embed=em)

    @github.command()
    async def display(self,ctx,url:str):
        is_valid = self.valid_url(url)
        if not is_valid:
            return await ctx.send("Link is invalid. Please provide a link like this one : `https://github.com/Esteban795/DiscordBot/blob/main/bot.py`")
        raw_content_url = self.url_converter(is_valid[0][0])
        file_extension = is_valid[0][1] 
        async with self.session.get(raw_content_url) as r:
            raw_code = await r.text()
        result = self.embed_builder(raw_code,file_extension)
        return await ctx.send(embed=result)

    @github.command()
    async def lines(self,ctx,start:int,end:int,url:str):
        await ctx.message.edit(suppress=True)
        if start < 0 or end < 0:
            return await ctx.send("'Start' and 'End' parameter must be integers greater than 0.")
        is_valid = self.valid_url(url)
        if not is_valid:
            return await ctx.send("Link is invalid. Please provide a link like this one : `https://github.com/Esteban795/DiscordBot/blob/main/bot.py`")
        raw_content_url = self.url_converter(is_valid[0][0])
        file_extension = is_valid[0][1]
        async with self.session.get(raw_content_url) as r:
            raw_code = await r.text()
        lines = raw_code.splitlines()
        result = self.embed_builder("\n".join(lines[start-1:end]),file_extension)
        return await ctx.send(embed=result)

def setup(bot):
    bot.add_cog(Github(bot))
    