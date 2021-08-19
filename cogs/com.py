import asyncio
from discord.ext import commands

class CustomOnMessage(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self._custom_on_message = {}
        self.bot.loop.create_task(self._cache_custom_on_message())

    async def _cache_custom_on_message(self):
        await self.bot.wait_until_ready()
        async with self.bot.db.execute("SELECT * FROM custom_on_message") as cursor:
            result = await cursor.fetchall()
        for message,call,guild_id in result:
            try:
                self._custom_on_message[guild_id][message] = call
            except KeyError: #The guild_id dict doesn't exist
                self._custom_on_message[guild_id] = {}
                self._custom_on_message[guild_id][message] = call

    @commands.Cog.listener()
    async def on_message(self,message):
        """
        This function gets called every time someone sends a message.

        ### Parameters : 
        - None. Only the content of the message matters, but it isn't a real parameter.

        ### Raises :
        - No error would be raised. Either there is a message that needs to be sent, either not.

        ### Returns :
        - The message that gets called every time a member says this specific message.

        ### Example : 

        "hi" is linked to "hello" in the database.

        Member says : hi
        Bot says : hello
        """
        if message.author == self.bot.user or not message.guild:
            return
        try:
            msg = self._custom_on_message[message.guild.id][message.content]
        except KeyError: #no custom on message found in the internal cache
            pass
        else:
            return await message.channel.send(msg)

    @commands.group(aliases=["com"],help="Does nothing without subcommands.")
    async def custom_on_message(self,ctx):
        """Nothing special here. You need to use subcommands."""
        if ctx.invoked_subcommand is None:
            return await ctx.send("Subcommand required.")
    
    @custom_on_message.command(help="Lets you add a custom on message to this server.")
    async def add(self,ctx,message,*,call):
        """
        Lets you add custom on_message to the bot. 
        ### /!\ This is server dependant, which means you can't use a custom on_message defined on a certain server on another server.
        ### /!\ Customs on_message AND what the bot will say MUST be quoted if they are more than one word.

        ### Usage example : 
        $CustomOnMessage add "You all are beautiful" "Thanks, you too !"

        or 

        $com add hello hey
        """
        check_if_exists = await self.bot.db.execute(f"SELECT message FROM custom_on_message WHERE message = ? AND guild_id = ?",(message,ctx.guild.id))
        exists = await check_if_exists.fetchone()
        if exists: #The custom on message already calls another message.
            return await ctx.send(f"'{message}' already calls an other message ! Pick another name (this is case sensitive).")
        await self.bot.db.execute(f"INSERT INTO custom_on_message VALUES(?,?,?)",(message,call,ctx.guild.id))
        await self.bot.db.commit()
        self._custom_on_message[ctx.guild.id][message] = call
        await ctx.send(f"Got it ! If anyone says '{message}', I will answer '{call}'.")

    @custom_on_message.command(help="Lets you remove a custom on message of this server.")
    async def remove(self,ctx,message):
        """
        Lets you remove customs on_message from the bot.
        ### /!\ This is server dependant, which means you can't use a custom on_message defined on a certain server on another server.

        ### Usage example :
        Let's say you used this command to add a custom on message previously.
        
        - $com add hello hey

        To remove it, you need to use :

        - $com remove hello

        To be more global, you need to use what calls the bot's answer.
        """
        check_if_exists = await self.bot.db.execute(f"SELECT message FROM custom_on_message WHERE message = ? AND guild_id = ?",(message,ctx.guild.id))
        exists = await check_if_exists.fetchone()
        if not exists:
            return await ctx.send("Uhm. Actually, this message doesn't call any message from me. Can't remove something that doesn't exist, right ?")
        try:
            await ctx.send(f"Are you sure you want to delete the `{message}` custom message ? Type 'yes' to confirm.")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and ctx.channel == m.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting process.")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute(f"DELETE FROM custom_on_message WHERE message = ? AND guild_id = ?",(message,ctx.guild.id))
                await self.bot.db.commit()
                del self._custom_on_message[message]
                return await ctx.send(f"Got it. I won't answer to '{message}' anymore !")
            return await ctx.send("Well, now I am not doing it.")


    @custom_on_message.command(help="Lets you edit a custom on message of this server.")
    async def edit(self,ctx,message,*,call):
        """
        Lets you edit custom on_message from the bot.
        #### /!\ This is server dependant, which means you can't use a custom on_message defined on a certain server on another server.

        ### Usage example :
        Let's say you used this command to add a custom on message previously.
        
        - $com add hello hey

        To edit it, you need to use :

        - $com edit hello hi

        To be more global, you need to use what calls the bot's answer.
        """
        check_if_exists = await self.bot.db.execute(f"SELECT message FROM custom_on_message WHERE message = ? AND guild_id = ?",(message,ctx.guild.id))
        exists = await check_if_exists.fetchone()
        if not exists:
            return await ctx.send("Uhm. Actually, this message doesn't call any message from me. Can't edit something that doesn't exist, right ?")
        await self.bot.db.execute(f"UPDATE custom_on_message SET call = ? WHERE message = ? and guild_id = ?",(call,message,ctx.guild.id))
        await self.bot.db.commit()
        self._custom_on_message[message] = call
        await ctx.send(f"Just edited what '{message}' calls. Now calls '{call}' ! ")

def setup(bot):
    bot.add_cog(CustomOnMessage(bot))