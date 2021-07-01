from dotenv import load_dotenv
import discord
import os
from discord.ext import commands
import aiosqlite
from datetime import datetime
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
        async with db.execute("SELECT custom_prefixes FROM prefixes WHERE guild_id = (?);",(message.guild.id,)) as cursor:
            result = await cursor.fetchone()
            if result is None:
                return "$"
            else:
                return result[0].split(" ") + ["$"]

load_dotenv()
bot = commands.Bot(command_prefix=get_prefix,description="A Chuck Norris dedicated discord bot !",intents=discord.Intents.all())

class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return  f'• `{self.clean_prefix}{command.qualified_name} {command.signature}`'

    async def send_bot_help(self, mapping):
        """Sends the bot help embed. This actually reveals every command registered in"""
        channel = self.get_destination() #Is ctx.channel
        embed = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="You asked for help, here I am.")
        for cog, commands in mapping.items(): #Iterate through every command cog and command registered (cog,[commands in the cog])
            filtered = await self.filter_commands(commands, sort=True) #Sort commands alphabetically
            command_signatures = [self.get_command_signature(c) for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)
        await channel.send(embed=embed)
    
    async def send_command_help(self, command):
        """Sends help for a specific command. This shows how you can use it. Example : $help kick will return $kick [member] (reason)"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="You asked for help, here I am.")
        emby.add_field(name="How to use this command : ",value=self.get_command_signature(command))
        if len(command.aliases):
            emby.add_field(name="Aliases you can use :",value=", ".join(command.aliases),inline=False)
        emby.add_field(name="Cooldown : ",value=command.cooldown_after_parsing,inline=False)
        await channel.send(embed=emby)
    
    async def send_group_help(self, group):
        """Sends help for a group of command. Specify a subcommand to get help from it too. Example : $help tags will show you $tag add, $tag remove etc"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.utcnow(),description="This command is actually a GROUP of command. Such awesome.")
        emby.add_field(name="Main command :",value=self.get_command_signature(group),inline=False)
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

initial_extensions = ["cogs.music","cogs.tags","cogs.eh","cogs.poll","cogs.logs","cogs.owner","cogs.prefix","cogs.com","cogs.xp","cogs.mod","cogs.chucknorris","cogs.reddit","cogs.python"]

for i in initial_extensions:
    try:
        bot.load_extension(i)
    except:
        print(f"Couldn't load {i}.")

bot.run(TOKEN)