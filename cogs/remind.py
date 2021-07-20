import discord
from discord.ext import commands,tasks
import datetime
from bot import TimeConverter
import typing

class Reminder(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.reminders_loop.start()

    @tasks.loop(seconds=30)
    async def reminders_loop(self):
        await self.bot.wait_until_ready()
        sql = "SELECT member_id,guild_id,reminder,channel_id,reminder_id FROM reminders WHERE remind_time <= ? AND reminded = 0;"
        async with self.bot.db.execute(sql,(datetime.datetime.utcnow().replace(microsecond=0),)) as cursor:
            async for row in cursor:
                try:
                    guild = self.bot.get_guild(row[1])
                    member = guild.get_member(row[0])
                    channel = self.bot.get_channel(row[3])
                    await channel.send(f"Alright {member.mention}, you asked me to remind this : {row[2]}")
                except AttributeError:
                    await self.bot.db.execute("DELETE FROM reminders WHERE guild_id = ?",(row[1],))
                    await self.bot.db.commit()
                else:
                    await self.bot.db.execute("UPDATE reminders SET reminded = 1 WHERE reminder_id = ?",(row[4],))
                    await self.bot.db.commit()
    
    @commands.command()
    async def remind(self,ctx,time:TimeConverter,*,reminder):
        remind_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
        await self.bot.db.execute("INSERT INTO reminders(member_id,guild_id,channel_id,reminder,remind_time) VALUES(?,?,?,?,?);",(ctx.author.id,ctx.guild.id,ctx.channel.id,reminder,remind_time.replace(microsecond=0)))
        await self.bot.db.commit()
        await ctx.send(f"Alright, {ctx.author.mention}, see you soon !")
                    
    @commands.command()
    async def todo(self,ctx,todo:typing.Union[int,str]=None):
        if ctx.invoked_subcommand is None:
            if not todo:
                sql = "SELECT to_do,done FROM todos WHERE list_id = (SELECT list_id FROm todolists WHERE member_id = ? AND guild_id = ?"
                l = []
                async with self.bot.db.execute(sql,(ctx.author.id,ctx.guild.id)) as cursor:
                    async for row in cursor:
                        emoji = "✓" if row[1] == 1 else "⨯"
                        l.append(f"• {row[0]} : {emoji}")
                em = discord.Embed(title=f"{ctx.author}'s to do list",color=0xaaffaa,timestamp=datetime.datetime.utcnow())

def setup(bot):
    bot.add_cog(Reminder(bot))