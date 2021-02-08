from dotenv import load_dotenv
from datetime import datetime
import discord
import os
from discord.ext import commands
import requests

load_dotenv()
bot = commands.Bot(command_prefix='$')
TOKEN = os.getenv('BOT_TOKEN') #Bot token needs to be stored in a .env file

@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.event
async def on_command_error(ctx,err:discord.errors):
    await ctx.send("NO WAY ! I'M EXPERIENCING TROUBLE. Joking. Investigating ! ")

@bot.event
async def on_message(message): # Writes any message send by users who are not this discord bot
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
async def chucknorris(ctx,*args):
    if len(args) == 0:
        r = requests.get("http://api.icndb.com/jokes/random")
        if r.json()['type'] == 'success': # checks if the request was a success
            await ctx.send(r.json()['value']['joke'])
        else:
            await ctx.send("Something went wrong. Investigating on it !")

@bot.command()
@commands.has_permissions(manage_roles = True)
async def giverole(ctx, user: discord.Member, role: discord.Role): # Gives "role" to "user"
    await user.add_roles(role)

@bot.command()
@commands.has_permissions(manage_roles = True)
async def removerole(ctx,user : discord.Member, role:discord.Role): #Removes "role" from "user"
    await user.remove_roles(role)

@bot.command()
@commands.has_permissions(kick_members = True)
async def kick(ctx, user: discord.Member, *string): #Kicks "user", and send them a DM with "discord guild they were kicked, by who and for what reason"
    reasons = " ".join(string)
    await user.send(f"You were kicked from {ctx.guild} by {ctx.author}. Reason : {reasons}")
    await user.kick(reason=reasons)

@bot.command()
@commands.has_permissions(manage_messages = True)
async def purge(ctx,Amount:int):
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
async def ban(ctx,user : discord.Member, *string): #Same as kick, but with ban
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
async def unban(ctx,person : str):
    bans = await ctx.guild.bans()
    for entry in bans:
        if "{0.name}#{0.discriminator}".format(entry.user) == person:
            user = await bot.fetch_user(entry.user.id)
            await ctx.guild.unban(user)
        else:
            if entry.user.name == person:
                user = await bot.fetch_user(entry.user.id)
                await ctx.guild.unban(user) 
                
bot.run(TOKEN)
