import discord
from discord.ext import commands
import aiosqlite
from difflib import get_close_matches
import typing

class Tags(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_remove(self,member):
        guild_id = f"_{member.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"UPDATE {guild_id} SET creator_id = 'Null' WHERE creator_id = ?",(member.id,))
            await db.commit()

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"CREATE TABLE IF NOT EXISTS _{guild.id}(tag_name TEXT,description TEXT,creator_id INT);")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/tags.db") as db:
            await db.execute(f"DROP TABLE _{guild.id};")
            await db.commit()
    
    @commands.group(invoke_without_command=True)
    async def tag(self,ctx,*,tag_name):
        guild_id = f"_{ctx.guild.id}"
        if ctx.invoked_subcommand is None:
            async with aiosqlite.connect("databases/tags.db") as db:
                async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = ?",(tag_name,)) as cursor:
                    desc = await cursor.fetchone()
                    if desc is not None:
                        await ctx.send(desc[0])
                    else:
                        tag_names_availables = await db.execute(f"SELECT tag_name FROM {guild_id}")
                        fetched_tag_names = [i[0] for i in await tag_names_availables.fetchall()]
                        matches = "\n".join(get_close_matches(tag_name,fetched_tag_names,n=3))
                        if len(matches) == 0:
                            return await ctx.send(f"I couldn't find anything close enough to '{tag_name}'. Try something else.")
                        else:
                            return await ctx.send(f"Tag '{tag_name}' not found. Maybe you meant :\n{matches}")
    @tag.command()
    async def all(self,ctx):
        guild_id = f"_{ctx.guild.id}"
        l = []
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT * FROM {guild_id}") as cursor:
                async for row in cursor:
                    l.append(f"{row[0]} : {row[1]}")
        if len(l) == 0:
            return await ctx.send("No tags registered on this server.")
        return await ctx.send("\n".join(l))
    
    @tag.command()
    async def createdby(self,ctx,member:typing.Union[discord.Member,int]=None):
        member = member or ctx.author
        guild_id = f"_{ctx.guild.id}"
        if member is int:
            member_id = member
        else:
            member_id = member.id
        l = []
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT tag_name,description FROM {guild_id} WHERE creator_id = ?",(member_id,)) as cursor:
                async for row in cursor:
                    l.append(f"{row[0]} : {row[1]}")
        if len(l) == 0:
            return await ctx.send("This member doesn't own any tags !")
        return await ctx.send("\n".join(l))
        
    @tag.command()
    async def add(self,ctx,tag_name,*,description):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description FROM {guild_id} WHERE tag_name = ?;",(tag_name,)) as cursor:
                desc = await cursor.fetchone()
            if desc is not None:
                await ctx.send(f"Tag '{tag_name}' already exists in the database. Please pick another tag name !")
            else:
                await db.execute(f"INSERT INTO {guild_id} VALUES(?,?,?)",(tag_name,description,ctx.author.id))
                await db.commit()
                await ctx.send(f"Successfully added '{tag_name}' tag.")
    
    @tag.command()
    async def edit(self,ctx,tag_name,*,description):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description,creator_id FROM {guild_id} WHERE tag_name = ?;",(tag_name,)) as cursor:
                desc = await cursor.fetchone()
            if desc is None:
                return await ctx.send(f"No tag named '{tag_name}', so you can't edit it. Please create it first.")
            elif desc[1] != ctx.author.id and desc[1] != "Null":
                return await ctx.send("You must own the tag to edit it. Or the person who created the tag left the server. Then everyone is free to edit or remove it.")
            else:
                await db.execute(f"UPDATE {guild_id} SET description = ? WHERE tag_name = ?",(description,tag_name))
                await db.commit()
                await ctx.send(f"Succesfully edited '{tag_name}' tag.")

    @tag.command()
    async def remove(self,ctx,*,tag_name):
        guild_id = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/tags.db") as db:
            async with db.execute(f"SELECT description,creator_id FROM {guild_id} WHERE tag_name = ?;",(tag_name,)) as cursor:
                desc = await cursor.fetchone()
            if desc is None:
                await ctx.send(f"No tag named '{tag_name}', so you can't remove it.")
            elif desc[1] != ctx.author.id and desc[1] != "Null":
                return await ctx.send("You must own the tag to remove it.")
            else:
                await db.execute(f"DELETE FROM {guild_id} WHERE tag_name = ?;",(tag_name,))                     
                await db.commit()
                await ctx.send(f"Successfully removed '{tag_name}' tag.")

def setup(bot):
    bot.add_cog(Tags(bot))