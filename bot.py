from dotenv import load_dotenv
from datetime import datetime
import discord
import os
from discord.ext import commands
import requests
import json
import time
import youtube_dl
import typing
load_dotenv()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"),description="A Chuck Norris dedicated discord bot !",intents=discord.Intents.all())
TOKEN = os.getenv('BOT_TOKEN') #Bot token needs to be stored in a .env file

ydl_opts = {
    'format':"bestaudio/best",
    "postprocessors":[{
        'key':'FFmpegExtractAudio',
        'preferredcodec':'mp3',
        'preferredquality':'256'
    }]
}
class ChuckNorris(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=["ck","kc"])
    async def chucknorris(self,ctx,*args):#chuck norris joke will be send to the channel
        l = len(args)
        try:
            if l > 0:
                r = requests.get(f"https://api.chucknorris.io/jokes/random?category={args[0].lower()}")
            else:
                r = requests.get("https://api.chucknorris.io/jokes/random")
            joke = r.json()["value"]
            categories = ",".join(r.json()["categories"]) if len(r.json()["categories"]) > 0 else "None"
            embedVar = discord.Embed(title=f"Categories : {categories}.",color=0xaaffaa)
            embedVar.add_field(name="This joke is provided to you by : Chuck Norris himself.",value=f"{joke}")
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        except KeyError:
            embedVar = discord.Embed(title=f'There are no such categories as "{args[0]}".',color=0xff0000)
            embedVar.add_field(name="Don't try to fool me, I'll know it.",value="I'm also telling Chuck Norris about this. Watch your back.")
            embedVar.set_image(url="https://voi.img.pmdstatic.net/fit/http.3A.2F.2Fprd2-bone-image.2Es3-website-eu-west-1.2Eamazonaws.2Ecom.2Fvoi.2Fvar.2Fvoi.2Fstorage.2Fimages.2Fmedia.2Fmultiupload-du-25-juillet-2013.2Fchuck-norris-pl.2F8633422-1-fre-FR.2Fchuck-norris-pl.2Ejpg/460x258/quality/80/chuck-norris-vend-la-maison-qui-a-servi-de-decor-a-walker-texas-ranger.jpg")
            embedVar.set_footer(text="Pshhh. If you have no clue what categories are available, type '$ckcategories' !")
            await ctx.send(embed=embedVar)
    
    @commands.command(aliases=["ckcat","ckc","ckcategoires"])
    async def ckcategories(self,ctx):
        embedVar = discord.Embed(title="The categories of joke the bot can tell you.",color=0xaaffaa)
        r = requests.get("https://api.chucknorris.io/jokes/categories")
        embedVar.add_field(name="Pick your favourite ! ",value="\n".join(["• {}".format(i) for i in r.json()]))
        await ctx.send(embed=embedVar)

class Moderation(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.command(aliases=["addrole","roleadd"])
    @commands.has_permissions(manage_roles=True)
    async def giverole(self,ctx,user:discord.Member,role:discord.Role):
        await user.add_roles(role)
        embedVar = discord.Embed(description=f"{user} was granted the {role} role.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["rmvrole"])
    @commands.has_permissions(manage_roles = True)
    async def removerole(self,ctx,user : discord.Member, role:discord.Role): # $removerole [member] [role]
        await user.remove_roles(role)
        embedVar = discord.Embed(description=f"{user} lost the {role} role.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["gtfo"])
    @commands.has_permissions(kick_members = True)
    async def kick(self,ctx, user: discord.Member, *,reason="Not specified."): # $kick [member] [reason]
        PMembed = discord.Embed(title="Uh oh. Looks like you did something quite bad !",color=0xff0000)
        PMembed.add_field(name=f"You were kicked from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
        await user.send(embed=PMembed)
        await user.kick(reason=reason)
        embedVar = discord.Embed(description=f"{user} was successfully kicked from the server.",color=0xaaffaa)
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=["banl","bl"])
    @commands.has_permissions(administrator = True)
    async def banlist(self,ctx): #Displays current banlist from the server
        bans = await ctx.guild.bans()
        if len(bans) == 0:
            embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
        else:
            embedVar = discord.Embed(title="Here are all the people banned on this server : ",color=0xaaffaa)
            pretty_list = ["• {}#{} for : {} ".format(entry.user.name,entry.user.discriminator,entry[0]) for entry in bans]
            embedVar.add_field(name=f"There are {len(pretty_list)} of them ! ",value="\n".join(pretty_list))
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)
    
    @commands.command(aliases=["b","bna"])
    @commands.has_permissions(ban_members = True)
    async def ban(self,ctx,user : discord.Member, *,reason="Not specified."): # $ban [user] [reason]
        embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
        embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reason}")
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        await user.send(embed=embedVar)
        await user.ban(reason=reason)

    @commands.command(aliases=["p","perrms"])
    @commands.has_permissions(administrator = True)
    async def perms(self,ctx,member:discord.Member):
        embedVar = discord.Embed(title=f"You asked for {member}'s permissions on {ctx.guild}.",color=0xaaaaff)
        embedVar.add_field(name="Here they are : ",value="\n".join(["• {}".format(i[0]) for i in member.guild_permissions if i[1] is True]))
        await ctx.author.send(embed=embedVar)

    @commands.command(aliases=["clear","clearmsg"])
    @commands.has_permissions(manage_messages = True) 
    async def purge(self,ctx,Amount:int): #Delete "Amount" messages from the current channel. $purge [int]
        await ctx.channel.purge(limit=Amount + 1)

    @commands.command(aliases=["u","unbna"])
    @commands.has_permissions(ban_members = True)
    async def unban(self,ctx,person,*,reason="Not specified."):
        bans = await ctx.guild.bans()
        if len(bans) == 0:
            embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
            return await ctx.send(embed=embedVar)
        elif person == "all":
            for entry in bans:
                user = await bot.fetch_user(entry.user.id)
                await ctx.guild.unban(user)
                embedVar = discord.Embed(title="All members have been successfully unbanned !",color=0xaaffaa)
                await ctx.send(embed=embedVar)
                return
        count = 0
        dictionary = dict()
        string = ""
        continuer = True
        for entry in bans:
            if "{0.name}#{0.discriminator}".format(entry.user) == person:
                user = await bot.fetch_user(entry.user.id)
                embedVar = discord.Embed(title="{0.name}#{0.discriminator} is now free to join us again !".format(entry.user),color=0xaaffaa)
                embedVar.set_footer(text=f"Requested by {ctx.author}.")
                await ctx.send(embed=embedVar)
                await ctx.guild.unban(user,reason)
                return
            elif entry.user.name == person:
                    count += 1
                    key = f"{count}- {entry.user.name}#{entry.user.discriminator}"
                    dictionary[key] = entry.user.id
                    string += f"{key}\n"
        if continuer:
            if count >= 1:
                embedVar = discord.Embed(title=f"Uh oh. According to what you gave me, '{person}', I found {count} {'person' if count == 1 else 'people'} named like this.",color=0xaaaaff)
                embedVar.add_field(name="Here is the list of them : ",value=string)
                embedVar.add_field(name="How to pick the person you want to unban ?",value="Just give me the number before their name !")
                embedVar.set_footer(text=f"Requested by {ctx.author}.")
                await ctx.send(embed=embedVar)   
                def check(m):
                    return m.author == ctx.author 
                ans = await bot.wait_for('message',check=check, timeout=10)
                
                try:
                    emoji = '\u2705'
                    lines = string.split("\n")
                    identifier = int(dictionary[lines[int("{0.content}".format(ans)) - 1]])
                    user = await bot.fetch_user(identifier)
                    await ctx.guild.unban(user)
                    await ans.add_reaction(emoji)
                    embedVar = discord.Embed(title="{0.name}#{0.discriminator} is now free to join us again !".format(user),color=0xaaffaa)
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await ctx.send(embed=embedVar)
                except:
                    emoji = '\u2705'
                    embedVar = discord.Embed(title="Uh oh. Something went wrong.",color=0xffaaaa)
                    embedVar.add_field(name="For some reasons, I couldn't unban the user you selected.",value="Please try again !")
                    embedVar.set_footer(text=f"Requested by {ctx.author}.")
                    await ctx.send(embed=embedVar)

            else:
                await ctx.send("I can't find anyone with username '{}'. Try something else !".format(person))

class LogsManagement(commands.Cog):
    def __init__(self,bot,path):
        self.bot = bot
        self.path = path

    @commands.Cog.listener()
    async def on_guild_join(self,guild):
        guild_id = guild.id
        if os.path.isdir("logs"):
            os.chdir("logs")
        if not os.path.isfile(f"logs_{guild_id}.txt"):
            with open(f"logs_{guild_id}.txt","w") as logs:
                logs.write(f"The log file for {guild} starts here. ID of the guild : {guild_id}. \n \n")

    @commands.Cog.listener()
    async def on_message(self,message):
        if os.path.isdir("logs"):
            os.chdir("logs")
        if message.author != bot.user:
            with open(f"logs_{message.guild.id}.txt","a") as logs_file:
                time = datetime.now()
                logs_file.write(f"{time} ||||| Message from {message.author} in text channel {message.channel.name} : {message.content} \n")

    @commands.Cog.listener()             
    async def on_guild_remove(self,guild):
        if os.path.isdir("logs"):
            os.chdir("logs")
        guild_id = guild.id
        os.remove(f"logs_{guild_id}.txt")
    
    @commands.command(aliases=["uplogs"])
    @commands.has_permissions(administrator=True)
    async def uploadlogs(self,ctx,channel:discord.TextChannel=None):
        try:
            if os.path.isdir("logs"):
                os.chdir("logs")
            await ctx.author.send(file=discord.File(f"logs_{ctx.guild.id}.txt"))
        except FileNotFoundError:
            embedVar = discord.Embed(title="Uh oh. Something went wrong.",
            description="The logs file for this guide doesn't exist. Want to create it ? Type 'yes if you want to create right now a log file !",
            color=0xff0000)
            embedVar.set_footer(text=f"Requested by {ctx.author}.")
            await ctx.send(embed=embedVar)

@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')


@bot.command()
async def echo(ctx, *args): #Repeat whatever you say
    await ctx.send(" ".join(args))

    
@bot.command()
async def owstats(ctx,platform,region,pseudo):
    p = '-'.join(pseudo.split('#'))
    r = requests.get(f"https://ow-api.com/v1/stats/{platform}/{region}/{p}/profile").json()
    await ctx.send(r)
    level = 100 * r["prestige"] +r["level"]
    embedvar = discord.Embed(title=f"{pseudo}'s statistics !",color=0xaaffaa)
    embedvar.add_field(name="Basic informations : ",value=f"• Level : {level}. \n • Endorsement level : {r['endorsement']}. \n • Carrier : {'private.' if r['private'] is True else 'public.'}")
    embedvar.set_thumbnail(url=r['icon'])
    embedvar.set_footer(text=f"Requested by {ctx.author}.")
    await ctx.send(embed=embedvar)

@bot.command()
async def play(ctx,url:str):
    if ctx.author.voice is None:
        embedVar = discord.Embed(title="Uh oh. Looks like something went wrong.",color=0xffaaaa)
        embedVar.add_field(name="You need to be in a voice channel to be able to let me sing you a song !",value="Please, join one before reentering this command.")
        embedVar.set_footer(text=f"Requested by {ctx.author}.")
        return await ctx.send(embed=embedVar)
    channel = ctx.author.voice.channel
    voice_client = await channel.connect()
    voice_client.play(discord.FFmpegPCMAudio(source=f"D:/CODE/DiscordBot/{url}",executable="C:/ffmpeg/bin/ffmpeg.exe"),after=lambda e:print("done",e))

@bot.command()
@commands.has_permissions(administrator=True)
async def spam(ctx,member):
    for i in range(50):
        await ctx.send(member)
    await ctx.channel.purge(limit=51)


bot.add_cog(ChuckNorris(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(LogsManagement(bot,os.getcwd()))

bot.run(TOKEN)