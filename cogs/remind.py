import discord
from discord.ext import commands,tasks
import datetime
from bot import TimeConverter
import typing

class Reminder(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.reminders_loop.start()

    async def _get_author_to_do_list_id(self,ctx):
        """Returns the to-do list's ID from a member. If the member doesn't have any to-do list setup, returns None."""
        async with self.bot.db.execute("SELECT list_id FROM todolists WHERE member_id = ? AND guild_id = ?",(ctx.author.id,ctx.guild.id)) as cursor:
            result = await cursor.fetchone()
        return result
    
    async def _todo_exists(self,list_id,to_do):
        """If the to-do exists in the list registered under list_id, then it returns the ID of the to-do."""
        async with self.bot.db.execute("SELECT to_do_id FROM todos WHERE list_id = ? AND to_do = ?",(list_id,to_do)) as cursor:
            result = await cursor.fetchone()
        return result

    async def reminder_task(self,r):
        member_id,guild_id,reminder,channel_id,reminder_id,remind_time = r
        t = datetime.datetime.strptime(remind_time,"%Y-%m-%d %H:%M:%S")
        await discord.utils.sleep_until(t)
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            await self.bot.db.execute("DELETE FROM reminders WHERE guild_id = ?",(guild_id,))
            await self.bot.db.commit()
            return
        if guild.unavailable:
            return
        member : discord.Member = guild.get_member(member_id)
        if member is None:
            await self.bot.db.execute("DELETE FROM reminders WHERE member_id = ?",(member_id,))
            await self.bot.db.commit()
            return
        try:
            channel = guild.get_channel(channel_id)
            await channel.send(f"Alright {member.mention}, you asked me to remind you this : {reminder} ! ")
        except AttributeError:
            await member.send(f"Alright {member.mention}, you asked me to remind you this : {reminder} ! ")
        except:
            return
        await self.bot.db.execute("UPDATE reminders SET reminded = 1 WHERE reminder_id = ?",(reminder_id,))
        await self.bot.db.commit()
        
    @tasks.loop(seconds=30)
    async def reminders_loop(self):
        await self.bot.wait_until_ready()
        sql = "SELECT member_id,guild_id,reminder,channel_id,reminder_id,remind_time FROM reminders WHERE CAST((julianday(remind_time) - julianday('now'))*86400 AS INTEGER) <= 30 AND reminded = 0;"
        async with self.bot.db.execute(sql) as cursor:
            async for row in cursor:
                await self.reminder_task(row)

    
    @commands.command()
    async def remind(self,ctx,time:TimeConverter,*,reminder):
        remind_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
        await self.bot.db.execute("INSERT INTO reminders(member_id,guild_id,channel_id,reminder,remind_time) VALUES(?,?,?,?,?);",(ctx.author.id,ctx.guild.id,ctx.channel.id,reminder,remind_time.replace(microsecond=0)))
        await self.bot.db.commit()
        await ctx.send(f"Alright, {ctx.author.mention}, see you soon !")
                    
    @commands.group(invoke_without_command=True,aliases=["todos"])
    async def todo(self,ctx,todo:typing.Union[int,str]=None):
        if ctx.invoked_subcommand is None:
            if not todo:
                sql = "SELECT to_do,done,importance FROM todos WHERE list_id = (SELECT list_id FROM todolists WHERE member_id = ? AND guild_id = ?) ORDER BY importance ASC;"
                l = []
                async with self.bot.db.execute(sql,(ctx.author.id,ctx.guild.id)) as cursor:
                    async for row in cursor:
                        emoji = "\U00002705" if row[1] == 1 else "\U0000274c"
                        l.append(f"{row[2]}.  {row[0]} : {emoji}")
                if len(l) == 0:
                    l = ["You don't have any to-dos yet !"]
                joined = "\n".join(l)
                em = discord.Embed(title=f"{ctx.author}'s to do list",color=0xaaffaa,timestamp=datetime.datetime.utcnow())
                em.add_field(name="\u2800",value=f"```md\n{joined}\n```")
                await ctx.send(embed=em)
    
    @todo.command()
    async def create(self,ctx,*,to_do=None):
        to_do_list_id = await self._get_author_to_do_list_id(ctx)
        if to_do_list_id:
            return await ctx.send("You can only have one to-do list per server.")
        insert = await self.bot.db.execute_insert("INSERT INTO todolists(member_id,guild_id) VALUES(?,?)",(ctx.author.id,ctx.guild.id))
        await self.bot.db.commit()
        to_do_list_id = insert[0]
        if to_do:
            await self.bot.db.execute("INSERT INTO todos(list_id,to_do,done,importance) VALUES(?,?,0,1)",(to_do_list_id,to_do))
            await self.bot.db.commit()
        return await ctx.send("Your to-do list for this server was created.")

    @todo.command()
    async def add(self,ctx,*,to_do):
        to_do_list_id = await self._get_author_to_do_list_id(ctx)
        if not to_do_list_id:
            return await ctx.send("You didn't setup a to-do list yet ! Create one using `?todo create <your first to do>` or simply `?todo create`.")
        to_do_exists = await self._todo_exists(to_do_list_id[0],to_do)
        if to_do_exists:
            return await ctx.send("Uhm. This to-do already exists in your list.")
        await self.bot.db.execute("INSERT INTO todos(list_id,to_do,done,importance) VALUES (?,?,0,1);",(to_do_list_id[0],to_do))
        await self.bot.db.commit()
        return await ctx.send(f"Successfully added {to_do} to your to-do list.")
    
    @todo.command()
    async def done(self,ctx,*,to_do):
        to_do_list_id = await self._get_author_to_do_list_id(ctx)
        if not to_do_list_id:
            return await ctx.send("You didn't setup a to-do list yet ! Create one using `?todo create <your first to do>` or simply `?todo create`.")
        to_do_exists = await self._todo_exists(to_do_list_id[0],to_do)
        if not to_do_exists:
            return await ctx.send("Uhm. This to-do doesn't exist.")
        await self.bot.db.execute("UPDATE todos SET done = 1 WHERE to_do_id = ?",(to_do_exists[0],))
        await self.bot.db.commit()
        return await ctx.send(f"{to_do} was set to 'Done'.")

    @todo.command()
    async def remove(self,ctx,*,to_do):
        to_do_list_id = await self._get_author_to_do_list_id(ctx)
        if not to_do_list_id:
            return await ctx.send("You didn't setup a to-do list yet ! Create one using `?todo create <your first to do>` or simply `?todo create`.")
        to_do_exists = await self._todo_exists(to_do_list_id[0],to_do)
        if not to_do_exists:
            return await ctx.send("Uhm. This to-do doesn't exist.")
        await self.bot.db.execute("DELETE FROM todos WHERE to_do_id = ?",(to_do_exists[0],))
        await self.bot.db.commit()
        return await ctx.send(f"Deleted to-do {to_do}.")
    
    @todo.command()
    async def edit(self,ctx,to_do,new_to_do):
        to_do_list_id = await self._get_author_to_do_list_id(ctx)
        if not to_do_list_id:
            return await ctx.send("You didn't setup a to-do list yet ! Create one using `?todo create <your first to do>` or simply `?todo create`.")
        to_do_exists = await self._todo_exists(to_do_list_id[0],to_do)
        if not to_do_exists:
            return await ctx.send("Uhm. This to-do doesn't exist.")
        await self.bot.db.execute("UPDATE todos SET to_do = ? WHERE to_do_id = ?",(new_to_do,to_do_exists[0]))
        await self.bot.db.commit()
        return await ctx.send(f"Successfully edited your to-do !")
    
    @todo.command()
    async def pending(self,ctx):
        sql = "SELECT to_do,importance FROM todos WHERE list_id = (SELECT list_id FROM todolists WHERE member_id = ? AND guild_id = ?)  AND done = 0 ORDER BY importance ASC;"
        l = []
        async with self.bot.db.execute(sql,(ctx.author.id,ctx.guild.id)) as cursor:
            async for row in cursor:
                l.append(f"{row[1]}. {row[0]} : \U0000274c")
        if len(l) == 0:
            l = ["No pending to-dos !"]
        em = discord.Embed(title=f"{ctx.author}'s to do list (pending only).T",color=0xaaffaa,timestamp=datetime.datetime.utcnow())
        joined = "\n".join(l)
        em.add_field(name="\u2800",value=f"```md\n{joined}\n```")
        return await ctx.send(embed=em)
    
    @todo.command()
    async def importance(self,ctx,n:int,*,to_do):
        to_do_list_id = await self._get_author_to_do_list_id(ctx)
        if not to_do_list_id:
            return await ctx.send("You didn't setup a to-do list yet ! Create one using `?todo create <your first to do>` or simply `?todo create`.")
        to_do_exists = await self._todo_exists(to_do_list_id[0],to_do)
        if not to_do_exists:
            return await ctx.send("Uhm. This to-do doesn't exist.")
        await self.bot.db.execute("UPDATE todos SET importance = ? WHERE to_do_id = ?",(n,to_do_exists[0]))
        await self.bot.db.commit()
        return await ctx.send(f"Changed importance of to-do {n}.")

def setup(bot):
    bot.add_cog(Reminder(bot))