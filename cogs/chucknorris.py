import aiohttp
import discord
from discord.ext import commands

class ChuckNorris(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=["cn","nc"])
    async def chucknorris(self,ctx,*args):
        """
        Use this to get the best Chuck Norris jokes. Usage : $chucknorris (a category, available with cncategories)
        
        ### Parameters : 
        - args : a category (available through $cncategories command)

        ### Raises :
        - KeyError : category doesn't exist.
        """
        l = len(args)
        try:
            if l > 0:
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(f"https://api.chucknorris.io/jokes/random?category={args[0].lower()}") as re:#Request to the API I'm using with a specific category
                        r = await re.json()
            else:
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(f"https://api.chucknorris.io/jokes/random") as re: #Request to the API I'm using,random joke this time
                        r = await re.json()
            joke = r["value"]
            categories = ",".join(r["categories"]) if len(r["categories"]) > 0 else "None"
            embedVar = discord.Embed(title=f"Categories : {categories}.",color=0xaaffaa)
            embedVar.add_field(name="This joke is provided to you by : Chuck Norris himself.",value=f"{joke}")
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        except KeyError: #Means the category doesn't exist on the API.
            embedVar = discord.Embed(title=f'There are no such categories as "{args[0]}".',color=0xff0000)
            embedVar.add_field(name="Don't try to fool me, I'll know it.",value="I'm also telling Chuck Norris about this. Watch your back.")
            embedVar.set_image(url="https://voi.img.pmdstatic.net/fit/http.3A.2F.2Fprd2-bone-image.2Es3-website-eu-west-1.2Eamazonaws.2Ecom.2Fvoi.2Fvar.2Fvoi.2Fstorage.2Fimages.2Fmedia.2Fmultiupload-du-25-juillet-2013.2Fchuck-norris-pl.2F8633422-1-fre-FR.2Fchuck-norris-pl.2Ejpg/460x258/quality/80/chuck-norris-vend-la-maison-qui-a-servi-de-decor-a-walker-texas-ranger.jpg")
            embedVar.set_footer(text="Pshhh. If you have no clue what categories are available, type '$ckcategories' !")
            await ctx.send(embed=embedVar)
    
    @commands.command(aliases=["cncat","cnc","cncategoires"])
    async def cncategories(self,ctx):
        """List the categories available from the API
        
        ### Parameters : 
        - None.

        ### Raises :
        - Nothing.

        ### Returns : 
        - A rich embed with the categories inside.
        """
        embedVar = discord.Embed(title="The categories of joke the bot can tell you.",color=0xaaffaa)
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.chucknorris.io/jokes/categories") as re: #Request to the API I'm using,random joke this time
                r = await re.json()
        embedVar.add_field(name="Pick your favourite ! ",value="\n".join(["• {}".format(i) for i in r]))
        await ctx.send(embed=embedVar)

def setup(bot):
    bot.add_cog(ChuckNorris(bot))