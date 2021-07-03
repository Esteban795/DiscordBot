from discord import message
from discord.errors import HTTPException
from discord.ext import commands
import discord
from PIL import Image,ImageDraw
import re
import aiohttp
import io
import functools

from discord.ext.commands.core import command

class ImageProcessing(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    def _blend(self,args):
        def change_image_size(max_width, max_height, image):
            width_ratio  = max_width / image.size[0]
            height_ratio = max_height / image.size[1]
            newWidth    = int(width_ratio * image.size[0])
            newHeight   = int(height_ratio * image.size[1])
            newImage    = image.resize((newWidth, newHeight))
            return newImage

        transparency = args[0]
        img1 = args[1]
        img2 = args[2]

        image1 = change_image_size(1920,1080,Image.open(img1)).convert("RGBA")  
        image2 = change_image_size(1920,1080,Image.open(img2)).convert("RGBA")

        alpha_blended = Image.blend(image1,image2,transparency) 

        byte_io = io.BytesIO()
        alpha_blended.save(byte_io,"PNG")
        byte_io.seek(0)
        file = discord.File(fp=byte_io,filename="test.png")
        return file

    def _resize(self,args):
        img = args[1]
        width = args[0]
        image = Image.open(img)
        w,h = image.size
        ratio = h/w
        newsize = (width,int(width * ratio))
        new_image = image.resize(newsize)
        byte_io = io.BytesIO()
        new_image.save(byte_io,"PNG")
        byte_io.seek(0)
        file = discord.File(fp=byte_io,filename="test.png")
        return file

    def _rotate(self,args):
        angle = args[0]
        img = args[1]
        image = Image.open(img).convert("RGBA")
        new_image = image.rotate(angle,expand=True,fillcolor=(0,0,0,0))
        byte_io = io.BytesIO()
        new_image.save(byte_io,"PNG")
        byte_io.seek(0)
        file = discord.File(fp=byte_io,filename="test.png")
        return file

    async def save_img(self,msg:discord.Message,n:int=1):
        discord_img_regex = re.compile(r"((?:https?:\/\/)?(?:media|cdn)\.discord(?:app)?\.(?:com|net)\/attachments\/(?:[0-9]+)\/(?:[0-9]+)\/(?:[\S]+)\.(?:png|jpg|jpeg|gif))")
        result = discord_img_regex.findall(msg.content)
        l = []
        for i in range(n):
            if result:
                url = result.pop(0)
            elif len(msg.attachments) and "image" in msg.attachments[0].content_type:
                url = msg.attachments.pop(0).url
            else:
                return
            async with aiohttp.ClientSession() as cs:
                async with cs.get(url) as image:
                    buffer = io.BytesIO(await image.read())
                    buffer.seek(0)
            l.append(buffer)
        return l

    async def run_image_processing(self,func,*args):
        t = functools.partial(func,args)
        m = await self.bot.loop.run_in_executor(None,t)
        return m

    @commands.command()
    async def resize(self,ctx,width:int,lien:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
            return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(self._resize,width,img)
        try:
            await ctx.send(content=f"{ctx.author.mention}, I'm done resizing your image !",file=f)
        except HTTPException as e:
            await ctx.send("File too large. I can't send this.")
        f.close()

    @commands.command()
    async def rotate(self,ctx,angle:int,lien:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
            return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(self._rotate,angle,img)
        try:
            await ctx.send(content=f"{ctx.author.mention}, I'm done rotating your image !",file=f)
        except HTTPException as e:
            await ctx.send("File too large. I can't send this.")
        f.close()
    
    @commands.command()
    async def blend(self,ctx,transparency:float,img1=None,img2=None):
        try:
            img1,img2 = await self.save_img(ctx.message,2)
        except TypeError:
            return await ctx.send("I need exactly two images to perform this command. Please, provide them. (upload one and give the discord image link for the other, or 2 discord image links).")
        f = await self.run_image_processing(self._blend,transparency,img1,img2)
        try:
            await ctx.send(content=f"{ctx.author.mention}, I'm done blending your images !",file=f)
        except HTTPException as e:
            await ctx.send("File too large. I can't send this.")
        f.close()

def setup(bot):
    bot.add_cog(ImageProcessing(bot))