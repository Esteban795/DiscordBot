from PIL import Image,ImageDraw,ImageFont
from math import floor,ceil
import aiosqlite
import discord
from discord.ext import commands
from datetime import datetime
import functools
import os
from bot import get_prefix
import asyncio
#Suite ag : 40*1.1**n - 30
class XPSystem(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1.0, 10.0, commands.BucketType.member)
        self.suite1 = "40*1.1**"
        self.suite2 = "-30"
        self.u0 = 10

    def ratelimit_check(self, message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_guild_join(self,guild:discord.Guild):
        async with aiosqlite.connect("databases/xp.db") as db:
            await db.execute(f"CREATE TABLE _{guild.id}(member_id INT,current_xp INT,next_level_xp INT,current_level INT);")
            await db.commit()
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        async with aiosqlite.connect("databases/xp.db") as db:
            await db.execute(f"DROP TABLE _{guild.id};")
            await db.commit() 

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        table_name = f"_{member.guild.id}"
        async with aiosqlite.connect("databases/xp.db") as db:
            await db.execute(f"DELETE FROM {table_name} WHERE member_id = ?",(member.id,))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self,message):
        retry_after = self.ratelimit_check(message)
        guild_prefix = tuple(await get_prefix(self.bot,message))
        if message.author.bot or message.content.startswith(guild_prefix) or not message.guild:
            return
        if retry_after is None:
            xp_won = 1 + ceil(min(len(message.content)/100,1) * 8)
            table_name = f"_{message.guild.id}"
            async with aiosqlite.connect("databases/xp.db") as db:
                cursor = await db.execute(f"SELECT current_xp,next_level_xp,current_level FROM {table_name} WHERE member_id = ?",(message.author.id,))
                result = await cursor.fetchone()
                if result:
                    current_xp = result[0] + xp_won
                    next_level_xp = result[1]
                    current_level = result[2]
                    if current_xp >= next_level_xp:
                        while current_xp >= next_level_xp:
                            current_xp -= next_level_xp
                            next_level_xp = floor(eval("".join([self.suite1,str(current_level + 1),self.suite2])))
                            current_level += 1
                        await db.execute(f"UPDATE {table_name} SET current_xp = ?,next_level_xp = ?,current_level = ? WHERE member_id = ?",(current_xp,next_level_xp,current_level,message.author.id))
                        await db.commit()
                        await message.channel.send(f"{message.author.mention} vient de passer au niveau {current_level} ! ")
                    else:
                        await db.execute(f"UPDATE {table_name} SET current_xp = ? WHERE member_id = ?",(current_xp,message.author.id))
                        await db.commit()
                else:
                    await db.execute(f"INSERT INTO {table_name} VALUES(?,?,?,0);",(message.author.id,xp_won,self.u0))
                    await db.commit()

    def xpcard(self,member_id,member_name,rank,level,xp,xp_level_suivant):
        FNT_30 = ImageFont.truetype("fonts/universcondensed.ttf", 30)
        FNT_25 = ImageFont.truetype("fonts/universcondensed.ttf", 25)
        FNT_20 = ImageFont.truetype("fonts/universcondensed.ttf", 20)
        avatar = Image.open(f'avatars/{member_id}_avatar.png').resize((125,125))

        background_to_crop = Image.new("L", avatar.size,color=0)
        im_rgba = avatar.copy()
        draw = ImageDraw.Draw(background_to_crop)
        draw.ellipse((0,0,125,125), fill=255)
        im_rgba.putalpha(background_to_crop)
        im_rgba_crop = im_rgba.crop((0,0,125,125))

        icon = im_rgba_crop.resize((125,125))

        img = Image.new("RGBA",(500,200),(70,70,70,255))
        d = ImageDraw.Draw(img)

        barre_xp = 200 + floor((xp/xp_level_suivant) * 250)
        d.rounded_rectangle([20,20,480,180],fill=(255,255,255,128),radius=5)
        d.rounded_rectangle([(200,130),(barre_xp ,150)],fill="red",radius=10)
        d.rounded_rectangle([(200,130),(450,150)],radius=10,width=3,outline="black")
        if len(member_name) > 12:
            d.text((200,105),text=member_name,font=FNT_20,fill=(0,0,0))
        else:
            d.text((200,100),text=member_name,font=FNT_30,fill=(0,0,0))
        d.text((370,25),text=f"Level : {level}",font=FNT_25,fill=(0,0,0))
        d.text((370,50),text=f"Rank : #{rank}",font=FNT_25,fill=(0,0,0))
        d.text((380,100),text=f"{xp}/{xp_level_suivant}xp",font=FNT_25,fill=(0,0,0))
        img.paste(icon,(50,40),icon)
        img.save(f"avatars/{member_id}_rank_card.png")

    async def run_xp_card(self,member_id,member,rank,current_level,current_xp,next_level_xp):
        t = functools.partial(self.xpcard,member_id,member,rank,current_level,current_xp,next_level_xp)
        m = await self.bot.loop.run_in_executor(None,t)

    @commands.command()
    async def rank(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        member_id = member.id
        table_name = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/xp.db") as db:
            cursor = await db.execute(f"SELECT current_xp,next_level_xp,current_level FROM {table_name} WHERE member_id = ?",(member_id,))
            result = await cursor.fetchone()
            if result:
                await member.avatar_url.save(f"avatars/{member_id}_avatar.png")
                await self.run_xp_card(member_id,str(member),10,result[2],result[0],result[1])
                await ctx.send(file=discord.File(f"avatars/{member_id}_rank_card.png"))
                os.remove(f"avatars/{member_id}_avatar.png")
                os.remove(f"avatars/{member_id}_rank_card.png")
            else:
                return await ctx.send("This member never spoke in the chat. How scary it is. Or they spoke in a channel I don't have access to. Either way, this ain't cool.")

    @commands.command(aliases=["levels"])
    async def ranking(self,ctx):
        l = []
        table_name = f"_{ctx.guild.id}"
        async with aiosqlite.connect("databases/xp.db") as db:
            async with db.execute(f"SELECT member_id,current_level FROM {table_name} ORDER BY current_level DESC,current_xp DESC;") as cursor:
                async for row in cursor:
                    member = ctx.guild.get_member(row[0])
                    l.append(f"• {member}. Level : {row[1]}")
        embed = discord.Embed(title=f"{ctx.guild}'s ranking".capitalize(),color=0x03fcc6,timestamp=datetime.utcnow(),description="\n".join(l))
        await ctx.send(embed=embed)

    @commands.group()
    @commands.has_permissions(administrator=True)
    async def reset(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Subcommand required.")

    @reset.command()
    async def all(self,ctx):
        try:
            await ctx.send("This will delete E.V.E.R.Y existing datas about your rank. No backup possible ! Type 'yes' to continue.")
            confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                table_name = f"_{ctx.guild.id}"
                async with aiosqlite.connect("databases/xp.db") as db:
                    await db.execute(f"DELETE FROM {table_name};")
                    await db.commit()
    
    @reset.command()
    async def member(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        try:
            await ctx.send(f"This will reset {member} levels. No backup possible ! Type 'yes' to continue.")
            confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                table_name = f"_{ctx.guild.id}"
                async with aiosqlite.connect("databases/xp.db") as db:
                    await db.execute(f"DELETE FROM {table_name} WHERE member_id = ?;",(member.id,))
                    await db.commit()

def setup(bot):
    bot.add_cog(XPSystem(bot))