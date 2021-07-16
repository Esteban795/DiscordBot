import asyncio
import discord
from discord.ext import commands
from difflib import get_close_matches
import datetime

class Tags(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.create_table_sql = """
        CREATE TABLE tags(tag_id INTEGER PRIMARY KEY AUTOINCREMENT,tag_name TEXT,tag_description TEXT, 
        creator_id INT,guild_id INT,uses INT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, alias_of INT)
        """

    async def _get_creator_id(self,tag_id:int)-> int:
        """Gives you the creator_id of a tag, given the tag_id (unique since it is a primary key.
        
        ### Parameters :
        - tag_id : unique integer.

        ### Returns :
        - creator_id : an integer. Allows you to then get the member/user through the bot.
        """
        sql = """SELECT creator_id FROM tags WHERE tag_id = ?"""
        async with self.bot.db.execute(sql,(tag_id,)) as cursor:
            result = await cursor.fetchone()
        return result[0]

    async def _tag_or_alias_exists(self,guild_id:int,tag_name:str)->int:
        """Check if a tag already exists, with a combo of his tag name and the guild's ID.
        
        ### Parameters : 
        - guild_id : integer, an ID.
        - tag_name : the name of the tag you need to get the tag_id (supposedly saved in the database).

        ### Returns :
        - tag_id : an integer, primary key from the table `tags`.
        - None : no tag named `tag_name` exists in the database with a guild_id = `guild_id parameter`.
        """
        tag_request = "SELECT tag_id FROM tags WHERE tag_name = ? AND guild_id = ?"
        async with self.bot.db.execute(tag_request,(tag_name,guild_id)) as cursor:
            tag_id = await cursor.fetchone()
            if tag_id:
                return tag_id[0]
        return None

    async def _tag_or_alias(self,tag_id:int)->str:
        """Checks if either the tag is an alias or an original tag.
        
        ### Parameters : 
        - tag_id : an integer, primary key from the table `tags`.

        ### Returns :
        - `tag` : tag_id is associated to an original tag.
        - `alias` : tag_id is associated to an alias.
        """
        async with self.bot.db.execute("SELECT alias_of FROM tags WHERE tag_id = ?",(tag_id,)) as cursor:
            result = await cursor.fetchone()
        if result[0]:
            return "alias"
        return "tag"

    async def _get_tag_only(self,tag_name:str)->int:
        """Looks for an original tag only (so aliases are being ignored here.
        ### Parameters :
        - tag_name : the name of the original tag you're looking for.

        ### Returns :
        - tag_id[0] : the tag ID associated with the tag name saved in the database.
        - None : no original tag named `tag_name` was found.
        """
        async with self.bot.db.execute("SELECT tag_id FROM tags WHERE tag_name = ? AND alias_of = 0;",(tag_name,)) as cursor:
            result = await cursor.fetchone()
        if result:
            return result[0]
        return None

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        """When a member leaves, all the tags they created/owned get their creator_id set to None. 
        This means anyone can then claim their tag.\n \n
        /!\ Tags are not deleted !
        """
        await self.bot.db.execute(f"UPDATE tags SET creator_id = ? WHERE creator_id = ?",(None,member.id))
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        """When the bot leaves a guild/gets kicked/banned, every tag created in this guild gets deleted.
        This is meant to not take much place."""
        await self.bot.db.execute("DELETE FROM tags WHERE guild_id = ?",(guild.id,))
        await self.bot.db.commit()
    
    @commands.group(invoke_without_command=True,aliases=["tags"])
    async def tag(self,ctx,*,tag_name:str)-> str:
        """Gets the tag content associated with the `tag_name` in the database.
        
        ### Parameters :
        - tag_name : a string, supposedly already saved in the database.

        ### Returns :
        - tag_desc : the tag content associated with the tag_name.
        - close_matches : close matches to tag_name, that could be what the user is looking for.
        - No close matches were found.
        """
        if ctx.invoked_subcommand is None:
            tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name) #Check if tag actually exists.If yes, tag's ID is stored inside tag_exists
            if tag_exists:
                async with self.bot.db.execute("SELECT tag_description,alias_of,uses FROM tags WHERE tag_id = ?",(tag_exists,)) as cursor: #Tag_description is what should be called when you do $tag [tag_name]
                    result = await cursor.fetchone()
                    tag_desc = result[0]
                    if result[1]: #Means alias_of isn't False, so this tag is actually an alias from another tag. result[1] is then the the tag_id of the original tag
                        async with self.bot.db.execute("SELECT tag_description FROM tags WHERE tag_id = ?",(result[1],)) as cursor: 
                            r = await cursor.fetchone()
                            tag_desc = r[0]
                    await self.bot.db.execute("UPDATE tags SET uses = ? WHERE tag_id = ?",(result[2] + 1,tag_exists))
                    await self.bot.db.commit()
                    return await ctx.send(tag_desc)
            else:
                async with self.bot.db.execute("SELECT tag_name FROM tags WHERE guild_id = ?",(ctx.guild.id,)) as cursor: #Gets every tag created in this server
                    all_tags = [i[0] for i in await cursor.fetchall()]
                    matches = "\n".join(get_close_matches(tag_name,all_tags,n=3)) #close matches to tag_name
                    if len(matches) == 0:
                        return await ctx.send(f"I couldn't find anything close enough to '{tag_name}'. Try something else.")
                    else:
                        return await ctx.send(f"Tag '{tag_name}' not found. Maybe you meant :\n{matches}")

    @tag.command(alias=["new","create"])
    async def add(self,ctx,tag_name:str,*,tag_description:str):
        """Creates a new tag, that you will be able to call later by using $tag [tag_name]
         - /!\ For tag's name with spaces, quote it. - Example : $tag add "this is a tag" this tag is very cool

        ### Parameters :
        - tag_name : a string, that will be use to call tag_description later.
        - tag_description : a string, that will be what the bot will send when you type $tag [tag_name].

        ### Returns :
        - A message that confirms everything went correctly.
        """
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if tag_exists:
            return await ctx.send(f"Tag or alias '{tag_name}' already exists.") #Can't have two same name for tags
        await self.bot.db.execute("INSERT INTO tags(tag_name,tag_description,creator_id,guild_id,uses,alias_of) VALUES(?,?,?,?,0,0);",(tag_name,tag_description,ctx.author.id,ctx.guild.id))
        await self.bot.db.commit()
        return await ctx.send(f"Tag '{tag_name}' created.")
    
    @tag.group(invoke_without_command=True,aliases=["tags"])
    async def remove(self,ctx,*,tag_name:str):
        """Removes an EXISITING tag from the database.
        
        ### Parameters : 
        - tag_name : a string, the name of the tag you want to remove.

        ### Returns : 
        - A message that confirms everything went correctly.
        """
        if ctx.invoked_subcommand is None:
            tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
            if not tag_exists:
                return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
            creator_id = await self._get_creator_id(tag_exists)
            if creator_id == ctx.author.id or ctx.author.guild_permissions.manage_guild: #Author of the command is the person who own the tag or author has manage guild permission (allows you to bypass remove and edit)
                await self.bot.db.execute("DELETE FROM tags WHERE tag_id = ?",(tag_exists,))
                await self.bot.db.execute("DELETE FROM tags WHERE alias_of = ?;",(tag_exists,))
                await self.bot.db.commit()
                return await ctx.send(f"Tag '{tag_name}' was deleted (and its aliases too).")
            return await ctx.send(f"You must be tag's owner or have 'manage server' permission to remove a tag.") #Author is neither the owner of the tag or has manage server permission

    @remove.command(name="all")
    async def _all(self,ctx):
        """Subcommand of `remove` command. Allows you to remove EVERY tags at once.
        
        ### Requires :
        - manage server permission.
        """
        if not ctx.author.guild_permissions.manage_guild: #Check for permissions of the author on the guild
            return await ctx.send("You must have 'manage guild' permission to perform this command.")
        try:
            await ctx.send("Are you sure you want to delete every tag created on this server ? Type 'yes' to continue. (No backup after that).")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Didn't answer in time. Aborting process.")
        else:
            if confirm.content == "yes":
                await self.bot.db.execute("DELETE FROM tags WHERE guild_id = ?",(ctx.guild.id,))
                await self.bot.db.commit()
                return await ctx.send("All tags were removed.")
            return await ctx.send("Aborting process.") #Answer is not "yes"
    
    @remove.command()
    async def aliases(self,ctx,*,tag_name):
        """Subcommand of `remove` command. Allows you to remove EVERY aliases of a tag at once.
        
        ### Requires :
        - manage server permission.
        """
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.send("You must have 'manage guild' permission to perform this command.")
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        try:
            await ctx.send(f"Are you sure you want to delete every aliases created for the tag '{tag_name}' ? Type 'yes' to continue. (No backup after that).")
            confirm = await self.bot.wait_for("message",check=lambda m:m.author == ctx.author and m.channel == ctx.channel,timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Didn't answer in time. Aborting process.")
        else:
            if confirm.content == "yes":
                await self.bot.db.execute("DELETE FROM tags WHERE guild_id = ? AND alias_of = ?",(ctx.guild.id,tag_exists)) #alias_of is an integer, the tag_id of the original tag this alias is associated to.
                await self.bot.db.commit()
                return await ctx.send(f"Done. All the aliases were removed.")
            return await ctx.send("Aborting process.")

    @tag.command()
    async def edit(self,ctx,tag_name:str,*,tag_description:str)->str:
        """Lets you edit a tag. This is shorter than deleting it and re-creating it, right ?
        
        ### Parameters :
        - tag_name : a string, the tag's name you want to edit.
        - tag_description : a string, the new tag content you want to edit.

        ### Returns : (either one of them)
        - tag_name doesn't exist in the database : a message telling you no tag named `tag_name` was found.
        - you're not the owner of the tag or don't have manage guild permission : a message that tells you can't edit it because blablabla
        - A message that confirms you everything went ok.
        - A message that tells you `tag_name` is actually an alias, and that `tag_description` isn't another tag_name. So edit doesn't work here.
        """
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        creator_id = await self._get_creator_id(tag_exists)
        if creator_id == ctx.author.id or ctx.author.guild_permissions.manage_guild:
            tag_or_alias = await self._tag_or_alias(tag_exists)  #checks whether the tag is an alias or an original tag
            if tag_or_alias == "tag":
                await self.bot.db.execute("UPDATE tags SET tag_description = ? WHERE tag_id = ?",(tag_description,tag_exists,))
            else:
                tag_only_exists = await self._get_tag_only(tag_description) #Checks if there is an original tag (no aliases here) called `tag_description`
                if not tag_only_exists:
                    return await ctx.send(f"'{tag_name}' is an alias, and then the second parameter must point to another EXISTING tag. But no tag named '{tag_description}' was found.")
                await self.bot.db.execute("UPDATE tags SET alias_of = ? WHERE tag_id = ?",(tag_only_exists,tag_exists))
            await self.bot.db.commit()
            return await ctx.send(f"Done. Tag '{tag_name}' edited.")
        return await ctx.send(f"You must be tag's owner or have 'manage server' permission to edit a tag.") #Not owner neither manage server permission
    
    @tag.command()
    async def alias(self,ctx,alias_name:str,*,referenced_tag:str):
        """Creates an alias for an original EXISTING tag.
        
        ### Parameters :
        - alias_name : a string, the future name of the alias.
        - referenced_tag : a string, that is the tag_name of an existing original tag.

        ### Returns : (either one of them)
        - A message that confirms everything went ok.
        - A message saying that no original tag named `referenced_tag` exists.
        """
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,alias_name)
        if tag_exists:
            return await ctx.send(f"Tag or alias '{alias_name}' already exists.")
        tag_only_exists = await self._get_tag_only(referenced_tag)
        if not tag_only_exists:
            return await ctx.send(f"No original tag named '{referenced_tag}' exists on this server. You can't use an alias for aliases !")
        await self.bot.db.execute("INSERT INTO tags(tag_name,tag_description,creator_id,guild_id,uses,alias_of) VALUES(?,?,?,?,0,?);",(alias_name,None,ctx.author.id,ctx.guild.id,tag_only_exists))
        await self.bot.db.commit()
        return await ctx.send(f"Done ! Alias '{alias_name}' now references to '{referenced_tag}'.")

    @tag.command()
    async def info(self,ctx,*,tag_name:str)->discord.Embed:
        """Givves you informations about a tag.
        
        ### Parameters : 
        - tag_name : a string, the name of the tag you want infos about.

        ### Returns : 
        - A message saying that no tag named `tag_name` exists in the database.
        - An embed with the infos (tag name, owner,id of the tag, when the tag was created, total times the tag was used)
        
        """
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        async with self.bot.db.execute("SELECT tag_name,creator_id,uses,created_at,alias_of FROM tags WHERE tag_id = ?",(tag_exists,)) as cursor: #gets tag infos thanks to tag_id
            tag_n,creator_id,uses,created_at,alias_of = await cursor.fetchone()
        em = discord.Embed(title=f"Tag : '{tag_n}'     (ID : {tag_exists}).",color=0x00ffaa,timestamp=datetime.datetime.utcnow())
        creator = ctx.guild.get_member(creator_id) or "They flew away.."
        em.add_field(name="Creator of this tag :",value=creator.mention)
        em.add_field(name="Uses :",value=uses)
        em.add_field(name="Created at :",value=created_at)
        if alias_of:
            async with self.bot.db.execute("SELECT tag_name FROM tags WHERE tag_id = ?",(alias_of,)) as cursor:
                result = await cursor.fetchone()
            original_tag = result[0]
            em.add_field(name="Is an alias for",value=original_tag)
        else:
            async with self.bot.db.execute("SELECT tag_name FROM tags WHERE alias_of = ?",(tag_exists,)) as cursor:
                aliases = ", ".join([i[0] for i in await cursor.fetchall()])
            em.add_field(name="Aliases :",value=aliases)
        return await ctx.send(embed=em)
    
    @tag.command()
    async def claim(self,ctx,*,tag_name:str)->str:
        """Allows you to claim a tag, means you become the new owner of this tag.
        
        ### Parameters :
        - tag_name : a string,the name of the tag you want to be the new owner.

        ### Requires : 
        - The tag must be free. If any creator_id is found in the database, you won't be able to become the new owner.

        ### Returns : (one of them)
        - A message that tells you the tag already has an owner.
        - A message that tells you you're the new owner, everything went ok.
        """
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        creator_id = await self._get_creator_id(tag_exists)
        if creator_id: #Someone already owns this tag.
            return await ctx.send("Uhm. The owner of this tag is still on the server, so they own what they created !")
        await self.bot.db.execute("UPDATE tags SET creator_id = ? WHERE tag_id = ?",(ctx.author.id,tag_exists))
        await self.bot.db.commit()
        return await ctx.send(f"You're now the owner of the tag '{tag_name}'.")
    
    @tag.command()
    async def free(self,ctx,*,tag_name:str)->str:
        """Allows you to free this tag, means you're no longer the owner of the tag.
        
        ### Parameters :
        - tag_name : a string,the name of the tag you want to free.

        ### Requires :
        - You must be the tag's current owner to perform this command.

        ### Returns : (one of them)
        - You're not the tag owner, so you can't free it.
        - Tag is now free, everything went ok.
        """
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        creator_id = await self._get_creator_id(tag_exists)
        if creator_id == ctx.author.id or ctx.author.guild_permissions.manage_guild:
            await self.bot.db.execute("UPDATE tags SET creator_id = ? WHERE tag_id = ?",(None,tag_exists))
            await self.bot.db.commit()
            return await ctx.send(f"Tag '{tag_name}' is now free to claim.")
        return await ctx.send("You must own the tag or have 'manage server' permission to free a tag !")

    @tag.command()
    async def createdby(self,ctx,member:discord.Member=None)-> discord.Embed:
        """Allows you to see at most the first ten tags created by the member.
        
        ### Parameters : 
        - member : a discord.Member instance.

        ### Returns :
        - An embed displaying the tags created by the member.
        """
        member = member or ctx.author #If member is not passed as an argument, then member becomes the author of the command
        async with self.bot.db.execute("SELECT tag_name FROM tags WHERE creator_id = ? AND guild_id = ?",(member.id,ctx.guild.id)) as cursor: #Gets every tag which has a creator_id == member.id
            tags = "\n".join([f"• {i[0]}" for i in await cursor.fetchall()][:10])
        if not tags: #Member didn't create any tag
            return await ctx.send("Uhm. This person hasn't created any tags.")
        async with self.bot.db.execute("SELECT COUNT(*)FROM tags WHERE creator_id = ?",(member.id,)) as cursor:
            result = await cursor.fetchone()
        count = result[0]
        em = discord.Embed(title=f"Tags owned by : {member} ({count} tags owned).",color=discord.Colour.blurple(),description=("*There are more than 10, but the embed would be massive if I displayed them all..*" if count > 10 else ""))
        em.add_field(name=(f"Here are the {count} tags created by this wholesome person :" if count <= 10 else f"Here are the first 10 tags created by this wholesome person :"),value=tags)
        return await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(Tags(bot))