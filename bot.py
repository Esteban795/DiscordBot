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
async def on_message(message): # Writes any message send by users who are not this discord bot
    if message.author != bot.user:
        with open("logs.txt","a") as logs_file:
            time = datetime.now()
            logs_file.write(f"{time} ||||| Message from {message.author} : {message.content} \n")
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
async def giverole(ctx, user: discord.Member, role: discord.Role): # Gives "role" to "user"
    await user.add_roles(role)

@bot.command()
async def removerole(ctx,user : discord.Member, role:discord.Role): #Removes "role" from "user"
    await user.remove_roles(role)

@bot.command()
async def kick(ctx, user: discord.Member, *string): #Kicks "user", and send them a DM with "discord they were kicked, by who and for what reason"
    reasons = " ".join(string)
    await user.send(f"You've been kicked from {ctx.guild} by {ctx.author}. Reason : {reasons}")
    await user.kick(reason=reasons)
    await ctx.author.send(f"{user} has been kicked successfully. Reason : {reasons}")

@bot.command()
async def ban(ctx,user : discord.Member, *string): #Same as kick, but with ban
    reasons = " ".join(string)
    await user.send(f"You were kicked banned from {ctx.guild} by {ctx.author}. Reason : {reasons}")
    await user.ban(reason=reasons)
    await ctx.author.send(f"{user} has been successfully banned. Reason : {reasons}")

@bot.command()
async def banlist(ctx): #Displays current banlist from the server
    bans = await ctx.guild.bans()
    if len(bans) == 0:
        await ctx.send("Uh oh. Looks like no one is currently banned on this server ! Keep it up.")
    else:
        banlist = ""
        for ban in bans:
            banlist += 'User "{}" was banned for {} \n'.format(ban[1],ban[0]) #ban[1] == name + discriminator from the banned user, ban[0] == reason they got banned for
        await ctx.send(banlist)

bot.run(TOKEN)