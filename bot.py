import aiohttp
from dotenv import load_dotenv
import discord
import os
from discord.ext import commands
import aiosqlite
from datetime import date, datetime
import re


time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])") #Detects patterns like "12d","10m"
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time

async def get_prefix(bot,message):
    """A callable that allows us to register custom prefixes"""
    if not message.guild:
        return "$"
    async with aiosqlite.connect("databases/main.db") as db:
        async with db.execute("SELECT prefix FROM prefixes WHERE guild_id = ?;",(message.guild.id,)) as cursor:
            result = await cursor.fetchall()
            if result is None:
                return "$"
            else:
                return [i[0] for i in result] + ["$"]

load_dotenv()
bot = commands.Bot(command_prefix=get_prefix,description="A Chuck Norris dedicated discord bot !",intents=discord.Intents.all())

class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return  f'• `{self.clean_prefix}{command.qualified_name} {command.signature}`'

    async def send_bot_help(self, mapping):
        """Sends the bot help embed. This actually reveals every command registered in"""
        channel = self.get_destination() #Is ctx.channel
        embed = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="You asked for help, here I am.")
        cogs = [cog.qualified_name for cog in mapping.keys() if getattr(cog,"qualified_name","No Category") != "No Category"]
        embed.add_field(name="Modules : ",value=f"`{', '.join(cogs)}`")
        rest = f"```Every parameter for the commands match one of these : \n • [foo] : parameter 'foo' has a default value. This means you don't HAVE TO give anything here. \n • <foo> : parameter 'foo' doesn't have a given value. You HAVE TO give something here to the bot !```"
        embed.add_field(name="\u200B",value=rest,inline=False)
        await channel.send(embed=embed)
    
    async def send_command_help(self, command):
        """Sends help for a specific command. This shows how you can use it. Example : $help kick will return $kick [member] (reason)"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="You asked for help, here I am.")
        emby.add_field(name="How to use this command : ",value=self.get_command_signature(command))
        if len(command.aliases) > 0:
            emby.add_field(name="Aliases you can use :",value=", ".join(command.aliases),inline=False)
        emby.add_field(name="Cooldown : ",value=command.cooldown_after_parsing,inline=False)
        await channel.send(embed=emby)
    
    async def send_group_help(self, group):
        """Sends help for a group of command. Specify a subcommand to get help from it too. Example : $help tags will show you $tag add, $tag remove etc"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="This command is actually a GROUP of command. Such awesome.")
        emby.add_field(name="Main command :",value=self.get_command_signature(group),inline=False)
        if len(group.aliases):
            emby.add_field(name="Aliases you can use :",value=", ".join(group.aliases),inline=False)
        emby.add_field(name="Subcommands : ",value="\n".join([self.get_command_signature(i) for i in group.commands]))
        await channel.send(embed=emby)

    async def send_cog_help(self, cog):
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description=f"**{cog.qualified_name} category**")
        filtered = await self.filter_commands(cog.get_commands(),sort=True)
        command_signatures = [self.get_command_signature(c) for c in filtered]
        emby.add_field(name="Commands : ",value="\n".join(command_signatures))
        await channel.send(embed=emby)
        
bot.help_command= MyHelp() #A custom help command.
TOKEN = os.getenv('BOT_TOKEN') #Bot token needs to be stored in a .env file

@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.command()
async def echo(ctx,*,args):
    await ctx.send(args)

   
initial_extensions = ["cogs.xp","cogs.music","cogs.tags","cogs.eh","cogs.poll","cogs.logs","cogs.owner","cogs.prefix","cogs.com","cogs.mod","cogs.chucknorris","cogs.reddit","cogs.python","cogs.image","cogs.gh"]

for i in initial_extensions:
    try:
        bot.load_extension(i)
    except:
        print(f"Couldn't load {i}.")

async def connect_db():
    async with aiohttp.ClientSession() as cs:
        bot.cs = cs
        bot.db = await aiosqlite.connect("databases/main.db")
        bot.no_mentions = discord.AllowedMentions.none()

bot.loop.run_until_complete(connect_db())
bot.run(TOKEN)