from dotenv import load_dotenv
from datetime import datetime
import discord
import os
from discord.ext import commands
import requests

load_dotenv()
bot = commands.Bot(command_prefix='$')
TOKEN = os.getenv('BOT_TOKEN')


@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author != bot.user:
        with open("logs.txt","a") as logs_file:
            time = datetime.now()
            logs_file.write(f"{time} ||||| Message from {message.author} : {message.content} \n")
    await bot.process_commands(message)

@bot.command()
async def echo(ctx,*args):
    await ctx.send(" ".join(args))

dico
@bot.command()
async def chucknorris(ctx,message):
    r = requests.get("http://api.icndb.com/jokes/random")
    if r.json()['type'] == 'success':
        await ctx.send(r.json()['value']['joke'])

bot.run(TOKEN)