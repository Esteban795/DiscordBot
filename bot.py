from dotenv import load_dotenv
from datetime import datetime
import discord
import os
from discord.ext import commands
import requests
from random import randint

load_dotenv()
bot = commands.Bot(command_prefix='$')
TOKEN = os.getenv('BOT_TOKEN') #Bot token needs to be stored in a .env file

@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.event
async def on_message(message): # logs file
    if message.author != bot.user:
        with open("logs.txt","a") as logs_file:
            time = datetime.now()
            logs_file.write(f"{time} ||||| Message from {message.author} : {message.content} \n")
    if message.content.lower() in ["hello",'hi','greetings','greet','hi there']:
        await message.channel.send("Hey {} !".format(message.author.display_name))
    await bot.process_commands(message)

@bot.command()
async def echo(ctx, *args): #Repeat whatever you say
    await ctx.send(" ".join(args))

@bot.command()
async def ck(ctx,*args):
    await chucknorris(ctx," ".join(args))

@bot.command()
async def chucknorris(ctx,*args):#chuck norris joke will be send to the channel
    l = len(args[0])
    try:
        if l > 0:
            r = requests.get(f"https://api.chucknorris.io/jokes/random?category={args[0].lower()}")
        else:
            r = requests.get("https://api.chucknorris.io/jokes/random")
        joke = r.json()["value"]
        categories = ",".join(r.json()["categories"]) if len(r.json()["categories"]) > 0 else "None"
        embedVar = discord.Embed(title=f"Categories : {categories}.",color=0xaaffaa)
        embedVar.add_field(name="This joke is provided to you by : Chuck Norris himself.",value=f"{joke}")
        await ctx.send(embed=embedVar)
    except KeyError:
        embedVar = discord.Embed(title=f'There are no such categories as "{args[0]}".',color=0xff0000)
        embedVar.add_field(name="Don't try to fool me, I'll know it.",value="I'm also telling Chuck Norris about this. Watch your back.")
        embedVar.set_image(url="https://voi.img.pmdstatic.net/fit/http.3A.2F.2Fprd2-bone-image.2Es3-website-eu-west-1.2Eamazonaws.2Ecom.2Fvoi.2Fvar.2Fvoi.2Fstorage.2Fimages.2Fmedia.2Fmultiupload-du-25-juillet-2013.2Fchuck-norris-pl.2F8633422-1-fre-FR.2Fchuck-norris-pl.2Ejpg/460x258/quality/80/chuck-norris-vend-la-maison-qui-a-servi-de-decor-a-walker-texas-ranger.jpg")
        embedVar.set_footer(text="Pshhh. If you have no clue what categories are available, type '$ckcategories' !")
        await ctx.send(embed=embedVar)

@bot.command()
async def ckcategories(ctx):
    embedVar = discord.Embed(title="The categories of joke the bot can tell you.",color=0xaaffaa)
    r = requests.get("https://api.chucknorris.io/jokes/categories")
    embedVar.add_field(name="Pick your favourite ! ",value="\n".join(["• {}".format(i) for i in r.json()]))
    await ctx.send(embed=embedVar)
@bot.command()
@commands.has_permissions(manage_roles = True)
async def giverole(ctx, user: discord.Member, role: discord.Role): # $giverole [member] [role]
    await user.add_roles(role)
    await ctx.send(f'**{user}** now has the {role} role !')
@bot.command()
@commands.has_permissions(manage_roles = True)
async def removerole(ctx,user : discord.Member, role:discord.Role): # $removerole [member] [role]
    await user.remove_roles(role)
    await ctx.send(f'**{user}** just lost the {role} role !')
@bot.command()
@commands.has_permissions(kick_members = True)
async def kick(ctx, user: discord.Member, *string): # $kick [member] [reason]
    reasons = " ".join(string)
    embedVar = discord.Embed(title="Uh oh. Looks like you did something quite bad !",color=0xff0000)
    embedVar.add_field(name=f"You were kicked from {ctx.guild} by {ctx.author}.",value=f"Reason : {reasons}")
    await ctx.send(f"**{user}** was kicked from the server !")
    await user.send(embed=embedVar)
    await user.kick(reason=reasons)

@bot.command()
@commands.has_permissions(manage_messages = True) 
async def purge(ctx,Amount:int): #Delete "Amount" messages from the current channel. $purge [int]
    await ctx.channel.purge(limit=Amount + 1)
@bot.command()
@commands.has_permissions(administrator = True)
async def banlist(ctx): #Displays current banlist from the server
    bans = await ctx.guild.bans()
    if len(bans) == 0:
        embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
        await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(title="Here are all the people banned on this server : ",color=0xaaffaa)
        pretty_list = ["• {}#{} for : {} ".format(entry.user.name,entry.user.discriminator,entry[0]) for entry in bans]
        embedVar.add_field(name=f"There are {len(pretty_list)} of them ! ",value="\n".join(pretty_list))
        await ctx.send(embed=embedVar)
@bot.command()
@commands.has_permissions(ban_members = True)
async def ban(ctx,user : discord.Member, *string): # $ban [user] [reason]
    reasons = " ".join(string) if len(string) > 0 else "Not specified."
    embedVar = discord.Embed(title="Uh oh. Looks like you did something QUITE bad !",color=0xff0000)
    embedVar.add_field(name=f"You were banned from {ctx.guild} by {ctx.author}.",value=f"Reason : {reasons}")
    await user.send(embed=embedVar)
    await user.ban(reason=reasons)
@bot.command()
@commands.has_permissions(administrator = True)
async def perms(ctx,member:discord.Member):
    embedVar = discord.Embed(title=f"You asked for {member}'s permissions on {ctx.guild}.",color=0xaaaaff)
    embedVar.add_field(name="Here they are : ",value="\n".join(["• {} : {}".format(i[0],i[1]) for i in member.guild_permissions]))
    await ctx.author.send(embed=embedVar)




@bot.command()
@commands.has_permissions(ban_members = True)
async def unban(ctx,person,*args):
    bans = await ctx.guild.bans()
    if len(bans) == 0:
        embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
        await ctx.send(embed=embedVar)
        return
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
            print(f'User : {user}')
            embedVar = discord.Embed(title="{0.name}#{0.discriminator} is now free to join us again !".format(entry.user),color=0xaaffaa)
            embedVar.add_field(name="I can also send them a DM to tell them they were unbanned. Want me to do it ?",value="Type 'yes' if you want me to !")
            embedVar.set_footer(text="They will know the reason they were unbanned but also who unbanned them (other than me, your fellow bot) !")
            await ctx.send(embed=embedVar)
            def check(m):
                return m.author == ctx.author
            ans = await bot.wait_for('message',check=check,timeout=10)
            if ans.content.lower() == "yes":
                print("deban")
                """
                unbanDM = discord.Embed(title=f"Hello !  You just got unbanned from : {ctx.guild}.",color=0xaaffaa)
                unbanDM.add_field(name=f"{ans.author} decided to unban you. Why ? That's what they told me : {' '.join(args)}.",value="Please, make sure not to get banned again !")
                await user.send(embed=unbanDM)"""
                await ctx.send("deban")
                await user.send("deban")
            await ctx.guild.unban(user)
            continuer = False
            break
        elif entry.user.name == person:
                count += 1
                key = "{0.name}#{0.discriminator}".format(entry.user)
                dictionary[key] = entry.user.id
                string += "{}\n".format(key)
    if continuer:
        if count >= 1:
            await ctx.send("Watch out ! There are {} guys named '{}' who are banned. Take a look at who you want to unban :\n{}".format(count,person,string))   
            def check(m):
                return m.author == ctx.author 
            ans = await bot.wait_for('message',check=check, timeout= 10)
            lines = string.split("\n")
            identifier = int(dictionary[lines[int("{0.content}".format(ans)) - 1]])
            user = await bot.fetch_user(identifier)
            await ctx.guild.unban(user)
        else:
            await ctx.send("I can't find anyone with username '{}'. Try something else !".format(person))

@bot.command()
async def numberguessing(ctx,limit:int):
    await ctx.send("Let's go ! You will have 10 seconds to answer each time !")
    continuer = True
    score = 0
    randomnumber = randint(1,limit)
    while continuer:
        def check(m):
            return m.author == ctx.author
        response = await bot.wait_for('message',check=check,timeout=10)   
        answer = int("{0.content}".format(response))
        if answer == randomnumber:
            score += 1
            await ctx.send("It only took you {} tries to guess the number. Congrats !".format(score))
            continuer = False
        elif answer < randomnumber:
            score += 1
            await ctx.send("The number I have in mind is bigger !")
        elif answer > randomnumber:
            score += 1
            await ctx.send("The number I have in mind is smaller !")
@bot.command()
async def clearlogs(ctx):
    with open("logs.txt","w"):
        await ctx.send("I just cleared the log file !")

#Error handling !

async def error_displayer(ctx,error):
    if isinstance(error,commands.MissingPermissions):
        missing_perms = " or ".join([" ".join(i.split('_')) for i in error.missing_perms])
        embedVar = discord.Embed(title="Uh oh. Something is not going as expected.",color=0xff0000)
        embedVar.add_field(name=f"{ctx.author}, you don't have access to this command.",value=f"You require {missing_perms} permissions to do so !")
        await ctx.send(embed=embedVar)
    if isinstance(error,commands.MissingRequiredArgument):
        print(error.param)
@perms.error
async def perms_error(ctx,error):
    await error_displayer(ctx,error)
@ban.error
async def ban_error(ctx,error):
    await error_displayer(ctx,error)
@kick.error
async def kick_error(ctx,error):
    await error_displayer(ctx,error)
@unban.error
async def unban_error(ctx,error):
    await error_displayer(ctx,error)
@banlist.error
async def banlist_error(ctx,error):
    await error_displayer(ctx,error)
bot.run(TOKEN)