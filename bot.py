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
    if message.content.startswith('!hello'):
        embedVar = discord.Embed(title="Title", description="Desc", color=0xff0000)
        embedVar.add_field(name="Field1", value="hi",inline=False)
        embedVar.add_field(name="Field2", value="hi2", inline=False)
        embedVar.set_footer(text="footer") #if you like to
        embedVar.set_author(name="ESTEBAN",url="https://mhworld.kiranico.com/fr/items?type=1")
        embedVar.set_image(url="https://cdn.discordapp.com/attachments/517055031820812288/776081552118382592/20201109205815_1.jpg")
        embedVar.set_thumbnail(url="https://cdn.discordapp.com/attachments/517055031820812288/776081552118382592/20201109205815_1.jpg")
        await message.channel.send(embed=embedVar)
    await bot.process_commands(message)

@bot.command()
async def echo(ctx, *args): #Repeat whatever you say
    await ctx.send(" ".join(args))

@bot.command()
async def chucknorris(ctx,*args):#chuck norris joke will be send to the channel
    if len(args) == 0:
        r = requests.get("http://api.icndb.com/jokes/random")
        if r.json()['type'] == 'success': # checks if the request was a success
            joke = r.json()['value']['joke']
            joke_id = r.json()["value"]["id"]
            embedVar = discord.Embed(title=f"Joke n° {joke_id}.",color=0xaaffaa)
            embedVar.add_field(name="This joke is provided to you by : me.",value=f"{joke}")
            await ctx.send(embed=embedVar)
        else:
            embedVar = discord.Embed(title="I'm struggling.",color=0xff0000)
            embedVar.add_field(name="I couldn't get a joke. Is Chuck Norris DDoSing me ?",value="I'm investigating on it !")
            await ctx.send(embed=embedVar)

@bot.command()
@commands.has_permissions(manage_roles = True)
async def giverole(ctx, user: discord.Member, role: discord.Role): # $giverole [member] [role]
    await user.add_roles(role)
    await ctx.send(f'{user} now has the {role} role !')

@bot.command()
@commands.has_permissions(manage_roles = True)
async def removerole(ctx,user : discord.Member, role:discord.Role): # $removerole [member] [role]
    await user.remove_roles(role)
    await ctx.send(f'{user} just lost the {role} role !')

@bot.command()
@commands.has_permissions(kick_members = True)
async def kick(ctx, user: discord.Member, *string): # $kick [member] [reason]
    reasons = " ".join(string)
    embedVar = discord.Embed(title="Uh oh. Looks like you did something quite bad !",color=0xff0000)
    embedVar.add_field(name=f"You were kicked from {ctx.guild} by {ctx.author}.",value=f"Reason : {reasons}")
    await ctx.send(f"{user} was kicked from the server !")
    await user.send(embed=embedVar)
    await user.kick(reason=reasons)

@bot.command()
@commands.has_permissions(manage_messages = True) 
async def purge(ctx,Amount:int): #Delete "Amount" messages from the current channel. $purge [int]
    await ctx.channel.purge(limit=Amount + 2)

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
    perms = ""
    for i in member.guild_permissions:
        perms += "{} : {} \n".format(i[0],i[1])
    await ctx.author.send(perms)

@bot.command()
@commands.has_permissions(ban_members = True)
async def unban(ctx,person=None):
    bans = await ctx.guild.bans()
    if person is None:
        await ctx.send("You need to tell me who I need to unban !")
        return
    elif len(bans) == 0:
        embedVar = discord.Embed(title="Uh oh. Looks like no one is banned on this server. Those are good news !",color=0xaaffaa)
        await ctx.send(embed=embedVar)
        return
    elif person == "all":
        for entry in bans:
            user = await bot.fetch_user(entry.user.id)
            await ctx.guild.unban(user)
            return
    count = 0
    dictionary = dict()
    string = ""
    continuer = True
    for entry in bans:
        if "{0.name}#{0.discriminator}".format(entry.user) == person:
            user = await bot.fetch_user(entry.user.id)
            await ctx.send("{0.name}#{0.discriminator} is now free to join us again !".format(entry.user))
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
bot.run(TOKEN)