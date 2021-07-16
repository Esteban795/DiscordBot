import asyncio
from re import I
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

    async def _get_creator_id(self,tag_id):
        sql = """SELECT creator_id FROM tags WHERE tag_id = ?"""
        async with self.bot.db.execute(sql,(tag_id,)) as cursor:
            result = await cursor.fetchone()
        return result[0]

    async def _tag_or_alias_exists(self,guild_id:int,tag_name:str):
        tag_request = "SELECT tag_id FROM tags WHERE tag_name = ? AND guild_id = ?"
        async with self.bot.db.execute(tag_request,(tag_name,guild_id)) as cursor:
            tag_id = await cursor.fetchone()
            if tag_id:
                return tag_id[0]
        return None

    async def _tag_or_alias(self,tag_id):
        async with self.bot.db.execute("SELECT alias_of FROM tags WHERE tag_id = ?",(tag_id,)) as cursor:
            result = await cursor.fetchone()
        if result[0]:
            return "alias"
        return "tag"

    async def _get_tag_only(self,tag_name):
        async with self.bot.db.execute("SELECT tag_id FROM tags WHERE tag_name = ? AND alias_of = 0;",(tag_name,)) as cursor:
            result = await cursor.fetchone()
        if result:
            return result[0]
        return None

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        await self.bot.db.execute(f"UPDATE tags SET creator_id = ? WHERE creator_id = ?",(None,member.id))
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        await self.bot.db.execute("DELETE FROM tags WHERE guild_id = ?",(guild.id,))
        await self.bot.db.commit()
    
    @commands.group(invoke_without_command=True,aliases=["tags"])
    async def tag(self,ctx,*,tag_name):
        if ctx.invoked_subcommand is None:
            tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
            if tag_exists:
                async with self.bot.db.execute("SELECT tag_description,alias_of,uses FROM tags WHERE tag_id = ?",(tag_exists,)) as cursor:
                    result = await cursor.fetchone()
                    tag_desc = result[0]
                    if result[1]:
                        async with self.bot.db.execute("SELECT tag_description FROM tags WHERE tag_id = ?",(result[1],)) as cursor:
                            r = await cursor.fetchone()
                            tag_desc = r[0]
                    await self.bot.db.execute("UPDATE tags SET uses = ? WHERE tag_id = ?",(result[2] + 1,tag_exists))
                    await self.bot.db.commit()
                    return await ctx.send(tag_desc)
            else:
                async with self.bot.db.execute("SELECT tag_name FROM tags WHERE guild_id = ?",(ctx.guild.id,)) as cursor:
                    all_tags = [i[0] for i in await cursor.fetchall()]
                    matches = "\n".join(get_close_matches(tag_name,all_tags,n=3))
                    if len(matches) == 0:
                        return await ctx.send(f"I couldn't find anything close enough to '{tag_name}'. Try something else.")
                    else:
                        return await ctx.send(f"Tag '{tag_name}' not found. Maybe you meant :\n{matches}")

    @tag.command(alias=["new","create"])
    async def add(self,ctx,tag_name,*,tag_description):
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if tag_exists:
            return await ctx.send(f"Tag or alias '{tag_name}' already exists.")
        await self.bot.db.execute("INSERT INTO tags(tag_name,tag_description,creator_id,guild_id,uses,alias_of) VALUES(?,?,?,?,0,0);",(tag_name,tag_description,ctx.author.id,ctx.guild.id))
        await self.bot.db.commit()
        return await ctx.send(f"Tag '{tag_name}' created.")
    
    @tag.group(invoke_without_command=True,aliases=["tags"])
    async def remove(self,ctx,*,tag_name):
        if ctx.invoked_subcommand is None:
            tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
            if not tag_exists:
                return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
            creator_id = await self._get_creator_id(tag_exists)
            if creator_id == ctx.author.id or ctx.author.guild_permissions.manage_guild:
                await self.bot.db.execute("DELETE FROM tags WHERE tag_id = ?",(tag_exists,))
                await self.bot.db.execute("DELETE FROM tags WHERE alias_of = ?;",(tag_exists,))
                await self.bot.db.commit()
                return await ctx.send(f"Tag '{tag_name}' was deleted (and its aliases too).")
            return await ctx.send(f"You must be tag's owner or have 'manage server' permission to remove a tag.")

    @remove.command(name="all")
    async def _all(self,ctx):
        if not ctx.author.guild_permissions.manage_guild:
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
            return await ctx.send("Aborting process.")
    
    @remove.command()
    async def aliases(self,ctx,*,tag_name):
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
                await self.bot.db.execute("DELETE FROM tags WHERE guild_id = ? AND alias_of = ?",(ctx.guild.id,tag_exists))
                await self.bot.db.commit()
                return await ctx.send(f"Done. All the aliases were removed.")
            return await ctx.send("Aborting process.")

    @tag.command()
    async def edit(self,ctx,tag_name,*,tag_description):
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        creator_id = await self._get_creator_id(tag_exists)
        if creator_id == ctx.author.id or ctx.author.guild_permissions.manage_guild:
            tag_or_alias = await self._tag_or_alias(tag_exists)
            if tag_or_alias == "tag":
                await self.bot.db.execute("UPDATE tags SET tag_description = ? WHERE tag_id = ?",(tag_description,tag_exists,))
            else:
                tag_only_exists = await self._get_tag_only(tag_description)
                if not tag_only_exists:
                    return await ctx.send(f"'{tag_name}' is an alias, and then the second parameter must point to another EXISTING tag. But no tag named '{tag_description}' was found.")
                await self.bot.db.execute("UPDATE tags SET alias_of = ? WHERE tag_id = ?",(tag_only_exists,tag_exists))
            await self.bot.db.commit()
            return await ctx.send(f"Done. Tag '{tag_name}' edited.")
        return await ctx.send(f"You must be tag's owner or have 'manage server' permission to edit a tag.")
    
    @tag.command()
    async def alias(self,ctx,alias_name,*,referenced_tag):
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
    async def info(self,ctx,*,tag_name):
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        async with self.bot.db.execute("SELECT tag_name,creator_id,uses,created_at,alias_of FROM tags WHERE tag_id = ?",(tag_exists,)) as cursor:
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
    async def claim(self,ctx,*,tag_name):
        tag_exists = await self._tag_or_alias_exists(ctx.guild.id,tag_name)
        if not tag_exists:
            return await ctx.send(f"Tag '{tag_name}' doesn't exist.")
        creator_id = await self._get_creator_id(tag_exists)
        if creator_id:
            return await ctx.send("Uhm. The owner of this tag is still on the server, so they own what they created !")
        await self.bot.db.execute("UPDATE tags SET creator_id = ? WHERE tag_id = ?",(ctx.author.id,tag_exists))
        await self.bot.db.commit()
        return await ctx.send(f"You're now the owner of the tag '{tag_name}'.")
    
    @tag.command()
    async def free(self,ctx,*,tag_name):
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
    async def createdby(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        async with self.bot.db.execute("SELECT tag_name FROM tags WHERE creator_id = ?",(member.id,)) as cursor:
            tags = "\n".join([f"• {i[0]}" for i in await cursor.fetchall()][:10])
        if not tags:
            return await ctx.send("Uhm. This person hasn't created any tags.")
        async with self.bot.db.execute("SELECT COUNT(*)FROM tags WHERE creator_id = ?",(member.id,)) as cursor:
            result = await cursor.fetchone()
        count = result[0]
        em = discord.Embed(title=f"Tags owned by : {member} ({count} tags owned).",color=discord.Colour.blurple(),description=("*There are more than 10, but the embed would be massive if I displayed them all..*" if count > 10 else ""))
        em.add_field(name=(f"Here are the {count} tags created by this wholesome person :" if count <= 10 else f"Here are the first 10 tags created by this wholesome person :"),value=tags)
        return await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Tags(bot))