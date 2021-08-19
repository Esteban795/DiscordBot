import discord
from discord.ext import commands,tasks
from bot import TimeConverter
import datetime

class Poll(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.emote_alphabet = ["\U0001F1E6","\U0001F1E7","\U0001F1E8","\U0001F1E9","\U0001F1EA","\U0001F1EB","\U0001F1EC","\U0001F1ED","\U0001F1EE","\U0001F1EF","\U0001F1F0","\U0001F1F1","\U0001F1F2","\U0001F1F3","\U0001F1F4",
    "\U0001F1F5","\U0001F1F6","\U0001F1F7","\U0001F1F8","\U0001F1F9"]
        self._timedpoll_loop.start()

    async def _create_poll_ended_embed(self,original_message,question,propositions)->discord.Embed:
        """Internal method to create a generic poll embed."""
        reactions_count = sorted([(original_message.reactions[i].count,i) for i in range(len(propositions))],key=lambda x:x[0],reverse=True)
        winner = reactions_count[0]
        embed = discord.Embed(title=f"Poll '{question.capitalize()}' just ended !",color=0xaaffaa,timestamp=datetime.datetime.utcnow(),description=f"Proposition '{propositions[winner[1]]}' won with {winner[0] - 1} votes !")
        return embed

    async def _timedpoll_task(self,args):
        channel_id,message_id,question,propositions = args
        channel = self.bot.get_channel(channel_id)
        try:
            original_message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await channel.send("Original poll message couldn't be found. Can't select the proposition who won !")
        else:
            em = await self._create_poll_ended_embed(original_message,question,propositions.split("\n"))
            await channel.send(embed=em)
            await self.bot.db.execute("DELETE FROM temppoll WHERE message_id = ?",(message_id,))
            await self.bot.db.commit()

    @tasks.loop(minutes=1)
    async def _timedpoll_loop(self):
        """A loop that checks """
        await self.bot.wait_until_ready()
        async with self.bot.db.execute("SELECT channel_id,message_id,question,propositions FROM temppoll WHERE end_time <=  ?",(datetime.datetime.utcnow(),)) as cursor:
            async for row in cursor:
                await self._timedpoll_task(row)

    @commands.command(aliases=["study"],help="Lets you create a poll. Keep two things in mind : every argument must be quoted if they aren't a single word, and the first argument will be the title of the poll.",
    brief="`$poll 'Apple or banana' 'Apple' 'Banana'` creates a poll with two choices : Apple and Banana.")
    async def poll(self,ctx,*args):
        if len(args) > 1:
            question = args[0].capitalize()
            try:
                choices = "\n".join([f'{self.emote_alphabet[i]}  {args[i + 1].capitalize()}' for i in range(len(args) - 1)])
                embed_poll = discord.Embed(title=question.capitalize(),description=choices,color=0xaaaaaa)
                embed_poll.set_footer(text=f"Requested by {ctx.author}.")
                message = await ctx.send(embed=embed_poll)
                for i in range(len(args) - 1):
                    await message.add_reaction(self.emote_alphabet[i])
            except IndexError:
                await ctx.send("Discord doesn't allow me to react with more than 20 emojis. So you can't have more than 20 choices for your poll.")
        else:
            return await ctx.send("I need at least the topic of the poll and an option. Please provide them both.")
    
    @commands.command(aliases=["tpoll"],help="Lets you create a poll that actually has a time limit. Keep two things in mind : every argument must be quoted if they aren't a single word, and the first argument will be the title of the poll.",
    brief="`$poll 'Apple or banana' 'Apple' 'Banana'` creates a poll with two choices : Apple and Banana.")
    async def timedpoll(self,ctx,time:TimeConverter,question,*args):
        if len(args) > 0:
            try:
                choices = "\n".join([f'{self.emote_alphabet[i]}  {args[i].capitalize()}' for i in range(len(args))])
                embed_poll = discord.Embed(title=question,description=choices,color=0xaaaaaa)
                current_time = datetime.datetime.utcnow()
                time_delta = datetime.timedelta(seconds=time)
                final_time = current_time + time_delta
                embed_poll.add_field(name="Expires on :",value="{}-{}-{} {}:{}".format(final_time.day,final_time.month,final_time.year,final_time.hour,final_time.minute))
                embed_poll.set_footer(text=f"Requested by {ctx.author}.")
                message = await ctx.send(embed=embed_poll)
                for i in range(len(args)):
                    await message.add_reaction(self.emote_alphabet[i])
                expires_on = datetime.timedelta(seconds=time) + datetime.datetime.utcnow()
                await self.bot.db.execute("INSERT INTO temppoll VALUES(?,?,?,?,?)",(ctx.channel.id,message.id,question,"\n".join(args),expires_on))
                await self.bot.db.commit()
            except IndexError as e:
                await ctx.send("Discord doesn't allow me to react with more than 20 emojis. So you can't have more than 20 choices for your poll.")
        else:
            await ctx.send("I need at least the topic of the poll and an option. Please provide them both.")

def setup(bot):
    bot.add_cog(Poll(bot))