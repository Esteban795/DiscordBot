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
async def chucknorris(ctx,*args):#chuck norris joke will be send to the channel
    if len(args) == 0:
        r = requests.get("http://api.icndb.com/jokes/random")
        if r.json()['type'] == 'success': # checks if the request was a success
            await ctx.send(r.json()['value']['joke'])
        else:
            await ctx.send("Something went wrong. Investigating on it !")

@bot.command()
@commands.has_permissions(manage_roles = True)
async def giverole(ctx, user: discord.Member, role: discord.Role): # $giverole [member] [role]
    await user.add_roles(role)

@bot.command()
@commands.has_permissions(manage_roles = True)
async def removerole(ctx,user : discord.Member, role:discord.Role): # $removerole [member] [role]
    await user.remove_roles(role)

@bot.command()
@commands.has_permissions(kick_members = True)
async def kick(ctx, user: discord.Member, *string): # $kick [member] [reason]
    reasons = " ".join(string)
    await user.send(f"You were kicked from {ctx.guild} by {ctx.author}. Reason : {reasons}")
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
        await ctx.send("Uh oh. Looks like no one is currently banned on this server ! Keep it up.")
    else:
        pretty_list = ["• {}#{} for : {} ".format(entry.user.name,entry.user.discriminator,entry[0]) for entry in bans]
        await ctx.send("**Ban list:** \n{}".format("\n".join(pretty_list)))

@bot.command()
@commands.has_permissions(ban_members = True)
async def ban(ctx,user : discord.Member, *string): # $ban [user] [reason]
    reasons = " ".join(string)
    await user.send(f"You were banned from {ctx.guild} by {ctx.author}. Reason : {reasons}")
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
    if person is None:
        await ctx.send("You need to tell me who I need to unban !")
        return
    bans = await ctx.guild.bans()
    if len(bans) == 0:
        await ctx.send("Uh oh. Looks like no one is currently banned on this server ! Keep it up.")
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


bot.run(TOKEN)