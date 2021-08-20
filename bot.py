import aiohttp
from dotenv import load_dotenv
import discord
import os
from discord.ext import commands
import aiosqlite
import datetime
import re

LANGUAGES = {
    'af': 'afrikaans',
    'sq': 'albanian',
    'am': 'amharic',
    'ar': 'arabic',
    'hy': 'armenian',
    'az': 'azerbaijani',
    'eu': 'basque',
    'be': 'belarusian',
    'bn': 'bengali',
    'bs': 'bosnian',
    'bg': 'bulgarian',
    'ca': 'catalan',
    'ceb': 'cebuano',
    'ny': 'chichewa',
    'zh-cn': 'chinese (simplified)',
    'zh-tw': 'chinese (traditional)',
    'co': 'corsican',
    'hr': 'croatian',
    'cs': 'czech',
    'da': 'danish',
    'nl': 'dutch',
    'en': 'english',
    'eo': 'esperanto',
    'et': 'estonian',
    'tl': 'filipino',
    'fi': 'finnish',
    'fr': 'french',
    'fy': 'frisian',
    'gl': 'galician',
    'ka': 'georgian',
    'de': 'german',
    'el': 'greek',
    'gu': 'gujarati',
    'ht': 'haitian creole',
    'ha': 'hausa',
    'haw': 'hawaiian',
    'iw': 'hebrew',
    'he': 'hebrew',
    'hi': 'hindi',
    'hmn': 'hmong',
    'hu': 'hungarian',
    'is': 'icelandic',
    'ig': 'igbo',
    'id': 'indonesian',
    'ga': 'irish',
    'it': 'italian',
    'ja': 'japanese',
    'jw': 'javanese',
    'kn': 'kannada',
    'kk': 'kazakh',
    'km': 'khmer',
    'ko': 'korean',
    'ku': 'kurdish (kurmanji)',
    'ky': 'kyrgyz',
    'lo': 'lao',
    'la': 'latin',
    'lv': 'latvian',
    'lt': 'lithuanian',
    'lb': 'luxembourgish',
    'mk': 'macedonian',
    'mg': 'malagasy',
    'ms': 'malay',
    'ml': 'malayalam',
    'mt': 'maltese',
    'mi': 'maori',
    'mr': 'marathi',
    'mn': 'mongolian',
    'my': 'myanmar (burmese)',
    'ne': 'nepali',
    'no': 'norwegian',
    'or': 'odia',
    'ps': 'pashto',
    'fa': 'persian',
    'pl': 'polish',
    'pt': 'portuguese',
    'pa': 'punjabi',
    'ro': 'romanian',
    'ru': 'russian',
    'sm': 'samoan',
    'gd': 'scots gaelic',
    'sr': 'serbian',
    'st': 'sesotho',
    'sn': 'shona',
    'sd': 'sindhi',
    'si': 'sinhala',
    'sk': 'slovak',
    'sl': 'slovenian',
    'so': 'somali',
    'es': 'spanish',
    'su': 'sundanese',
    'sw': 'swahili',
    'sv': 'swedish',
    'tg': 'tajik',
    'ta': 'tamil',
    'tt': 'tatar',
    'te': 'telugu',
    'th': 'thai',
    'tr': 'turkish',
    'tk': 'turkmen',
    'uk': 'ukrainian',
    'ur': 'urdu',
    'ug': 'uyghur',
    'uz': 'uzbek',
    'vi': 'vietnamese',
    'cy': 'welsh',
    'xh': 'xhosa',
    'yi': 'yiddish',
    'yo': 'yoruba',
    'zu': 'zulu',
}

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
bot = commands.Bot(command_prefix=get_prefix,description="A Chuck Norris dedicated discord bot !",intents=discord.Intents.all(),case_insensitive=True)

class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return  f'• `{self.clean_prefix}{command.qualified_name} {command.signature}`'

    async def send_bot_help(self, mapping):
        """Sends the bot help embed. This actually reveals every command registered in"""
        channel = self.get_destination() #Is ctx.channel
        embed = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.datetime.utcnow(),description="You asked for help, here I am.")
        cogs = [cog.qualified_name for cog in mapping.keys() if getattr(cog,"qualified_name","No Category") != "No Category"]
        embed.add_field(name="Modules : ",value=f"`{', '.join(cogs)}`")
        rest = f"```Every parameter for the commands match one of these : \n • [foo] : parameter 'foo' has a default value. This means you don't HAVE TO give anything here. \n • <foo> : parameter 'foo' doesn't have a given value. You HAVE TO give something here to the bot !```"
        embed.add_field(name="\u200B",value=rest,inline=False)
        embed.set_footer(text="If you don't give the right args, bot gets real mad.")
        await channel.send(embed=embed)
    
    async def send_command_help(self, command):
        """Sends help for a specific command. This shows how you can use it. Example : $help kick will return $kick [member] (reason)"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.datetime.utcnow(),description="You asked for help, here I am.")
        emby.add_field(name="How to use this command : ",value=self.get_command_signature(command))
        emby.add_field(name="Cooldown : ",value=command.cooldown_after_parsing,inline=True)
        emby.add_field(name="What does that command do : ",value=command.help,inline=False)
        emby.add_field(name="Example :",value=command.brief,inline=True)
        if len(command.aliases) > 0:
            fmt_aliases = ", ".join(command.aliases)
            emby.add_field(name="Aliases you can use :",value=f"`{fmt_aliases}`",inline=False)
        
        await channel.send(embed=emby)
    
    async def send_group_help(self, group:commands.Group):
        """Sends help for a group of command. Specify a subcommand to get help from it too. Example : $help tags will show you $tag add, $tag remove etc"""
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.datetime.utcnow(),description="This command is actually a GROUP of command. Such awesome.")
        emby.add_field(name="Main command :",value=self.get_command_signature(group),inline=True)
        emby.add_field(name="What does that command do : ",value=group.help,inline=True)
        emby.add_field(name="Example :",value=group.brief,inline=True)
        if len(group.aliases):
            emby.add_field(name="Aliases you can use :",value=", ".join(group.aliases),inline=False)
        emby.add_field(name="Subcommands : ",value="\n".join([self.get_command_signature(i) for i in group.commands]),inline=False)
        await channel.send(embed=emby)

    async def send_cog_help(self, cog):
        channel = self.get_destination()
        emby = discord.Embed(title="The cavalry is here ! 🎺",color=0x03fcc6,timestamp=datetime.datetime.utcnow(),description=f"**{cog.qualified_name} category**")
        filtered = await self.filter_commands(cog.get_commands(),sort=True)
        command_signatures = [self.get_command_signature(c) for c in filtered]
        emby.add_field(name="Commands : ",value="\n".join(command_signatures))
        await channel.send(embed=emby)
        
bot.help_command= MyHelp() #A custom help command.
BOT_TOKEN = os.getenv('BOT_TOKEN') #Bot token needs to be stored in a .env file

@bot.event
async def on_ready():
    print(f'Logged as {bot.user.name}')

@bot.command()
async def echo(ctx,*,args):
    await ctx.send(args)

initial_extensions = ["cogs.eh","cogs.giveaway","cogs.translate","cogs.remind","cogs.xp","cogs.music","cogs.tags","cogs.poll","cogs.logs","cogs.owner","cogs.prefix","cogs.com","cogs.mod","cogs.chucknorris","cogs.reddit","cogs.python","cogs.image","cogs.gh"]

for i in initial_extensions:
    try:
        bot.load_extension(i)
    except Exception as e:
        print(f"Couldn't load {i}.")
        print(e)
        
async def connect_db():
    bot.cs = aiohttp.ClientSession()
    bot.db = await aiosqlite.connect("databases/main.db")
    bot.no_mentions = discord.AllowedMentions.none()

bot.loop.run_until_complete(connect_db())
bot.run(BOT_TOKEN)