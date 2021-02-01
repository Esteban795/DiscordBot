from dotenv import load_dotenv
from datetime import datetime
import discord
import os
from discord.ext import commands

load_dotenv()
bot = commands.Bot(command_prefix='$')
TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author != bot.user:
        time = datetime.now()
        print(f"{time} ||||| Message from {message.author} : {message.content}")
    await bot.process_commands(message)

@bot.command()
async def echo(ctx,message):
    await ctx.send(message)
    
bot.run(TOKEN)