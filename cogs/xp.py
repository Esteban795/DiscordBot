from PIL import Image,ImageDraw,ImageFont
from math import floor,ceil
import io
import discord
from discord.errors import HTTPException
from discord.ext import commands
from datetime import datetime
import functools
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
    async def on_message(self,message):
        retry_after = self.ratelimit_check(message)
        guild_prefix = tuple(await get_prefix(self.bot,message))
        if message.author.bot or message.content.startswith(guild_prefix) or not message.guild:
            return
        if retry_after is None:
            xp_won = 1 + ceil(min(len(message.content)/100,1) * 8)
            async with self.bot.db.execute(f"SELECT current_xp,next_level_xp,current_level FROM xp WHERE member_id = ? and guild_id = ?",(message.author.id,message.guild.id)) as cursor:
                result = await cursor.fetchone()
            if result:
                current_xp = result[0] + xp_won
                next_level_xp = result[1]
                current_level = result[2]
                if current_xp >= next_level_xp:
                    current_xp -= next_level_xp
                    next_level_xp = floor(eval("".join([self.suite1,str(current_level + 1),self.suite2])))
                    current_level += 1
                    await self.bot.db.execute(f"UPDATE xp SET current_xp = ?,next_level_xp = ?,current_level = ? WHERE member_id = ? and guild_id = ?",(current_xp,next_level_xp,current_level,message.author.id,message.guild.id))
                    await self.bot.db.commit()
                    return await message.channel.send(f"{message.author.mention} is now level {current_level} ! ")
                else:
                    await self.bot.db.execute(f"UPDATE xp SET current_xp = ? WHERE member_id = ? AND guild_id = ?",(current_xp,message.author.id,message.guild.id))
                    await self.bot.db.commit()
            else:
                await self.bot.db.execute("INSERT INTO xp VALUES(?,?,?,?,0);",(message.author.id,message.guild.id,xp_won,self.u0))
                await self.bot.db.commit()

    def xpcard(self,img,member_name,rank,level,xp,xp_level_suivant):
        FNT_30 = ImageFont.truetype("fonts/universcondensed.ttf", 30)
        FNT_25 = ImageFont.truetype("fonts/universcondensed.ttf", 25)
        FNT_20 = ImageFont.truetype("fonts/universcondensed.ttf", 20)
        avatar = Image.open(img).resize((125,125))

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
        return img

    async def run_xp_card(self,ctx,img,name,rank,current_level,current_xp,next_level_xp):
        t = functools.partial(self.xpcard,img,name,rank,current_level,current_xp,next_level_xp)
        m = await self.bot.loop.run_in_executor(None,t)
        bytes_io = io.BytesIO()
        m.save(bytes_io,"PNG",quality=95)
        bytes_io.seek(0)
        file = discord.File(fp=bytes_io,filename="rank_card.png")
        try:
            await ctx.send(file=file)
        except HTTPException:
            return await ctx.send("Something went wrong, I'm investigating on it.")
        file.close()
        return

    @commands.command()
    async def rank(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        async with self.bot.db.execute(f"SELECT current_xp,next_level_xp,current_level FROM xp WHERE member_id = ? AND guild_id = ?",(member.id,ctx.guild.id)) as cursor:
            result = await cursor.fetchone()
        if result:
            bytes_io = io.BytesIO(await member.avatar_url_as(format="webp").read())
            await self.run_xp_card(ctx,bytes_io,str(member),10,result[2],result[0],result[1])
        else:
            return await ctx.send("This member never spoke in the chat. How scary it is. Or they spoke in a channel I don't have access to. Either way, this ain't cool.")

    @commands.command(aliases=["levels"])
    async def ranking(self,ctx):
        l = []
        count = 1
        async with self.bot.db.execute("SELECT member_id,current_level FROM xp WHERE guild_id = ? ORDER BY current_level DESC,current_xp DESC;",(ctx.guild.id,)) as cursor:
            async for row in cursor:
                member = ctx.guild.get_member(row[0])
                if member:
                    l.append(f"{count}.  {member.mention}. Level : {row[1]}")
                    count += 1
        embed = discord.Embed(title=f"{ctx.guild}'s ranking".capitalize(),color=0x03fcc6,timestamp=datetime.utcnow(),description="\n".join(l))
        return await ctx.send(embed=embed)

    @commands.group()
    @commands.has_permissions(administrator=True)
    async def reset(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Subcommand required.")

    @reset.command()
    @commands.has_permissions(administrator=True)
    async def all(self,ctx):
        try:
            await ctx.send("This will delete E.V.E.R.Y existing datas about people's rank on your server. No backup possible ! Type 'yes' to continue.")
            confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute(f"DELETE FROM xp WHERE guild_id = ?;",(ctx.guild.id,))
                await self.bot.db.commit()
    
    @reset.command()
    @commands.has_permissions(administrator=True)
    async def member(self,ctx,member:discord.Member=None):
        member = member or ctx.author
        try:
            await ctx.send(f"This will reset {member.mention} levels. No backup possible ! Type 'yes' to continue.",allowed_mentions=self.bot.no_mentions)
            confirm = await self.bot.wait_for("message",check=lambda m: m.author == ctx.author and m.channel == ctx.channel,timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("You didn't answer fast enough. Aborting mission !")
        else:
            if confirm.content.lower() == "yes":
                await self.bot.db.execute(f"DELETE FROM xp WHERE member_id = ? AND guild_id = ?;",(member.id,ctx.guild.id))
                await self.bot.db.commit()
                return await ctx.send(f"{member.mention} was brought back to 0.",allowed_mentions=self.bot.no_mentions)

def setup(bot):
    bot.add_cog(XPSystem(bot))