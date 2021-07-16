from discord.ext import commands
import discord
from PIL import Image,ImageDraw,ImageOps
import re
import aiohttp
import io
import functools
import cv2
import numpy as np

class ImageProcessing(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    def _swap1(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                r,g,b = img.getpixel((i,j))
                img.putpixel((i,j),(b,r,g))
        return img
        
    def _swap2(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                r,g,b = img.getpixel((i,j))
                img.putpixel((i,j),(g,b,r))
        return img

    def _swap3(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                r,g,b = img.getpixel((i,j))
                img.putpixel((i,j),(b,g,r))
        return img

    def _swap4(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                r,g,b = img.getpixel((i,j))
                img.putpixel((i,j),(r,b,g))
        return img

    def _swap5(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                r,g,b = img.getpixel((i,j))
                img.putpixel((i,j),(g,r,b))
        return img

    def _whiteblack(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                pixel = img.getpixel((i,j))
                avg = sum(pixel)//3
                if avg < 128:
                    pixel = (0,0,0)
                else:
                    pixel = (255,255,255)
                img.putpixel((i,j),pixel)
        return img

    def _sepia(self,args):
        img = Image.open(args[0])
        for i in range(img.width):
            for j in range(img.height):
                pixel = img.getpixel((i,j))
                r,g,b = pixel
                new_r = int((r * .393) + (g *.769) + (b * .189))
                new_g = int((r * .349) + (g *.686) + (b * .168))
                new_b = int((r * .272) + (g *.534) + (b * .131))
                img.putpixel((i,j),(new_r,new_g,new_b))
        return img

    def _solarize(self,args):
        n,img = args
        image = Image.open(img).convert("RGB")
        img = ImageOps.solarize(image,n)
        return img
    def _posterize(self,args):
        n,img = args
        image = Image.open(img).convert("RGB")
        img = ImageOps.posterize(image,n)
        return img
        
    def _mirror(self,args):
        img = Image.open(args[0])
        mirrored_img = ImageOps.mirror(img)
        return mirrored_img

    def _invert(self,args):
        img = Image.open(args[0]).convert("RGB")
        inverted_img = ImageOps.invert(img)
        byte_io = io.BytesIO()
        return inverted_img

    def _grayscale(self,args):
        img = Image.open(args[0])
        gray_img = ImageOps.grayscale(img)
        byte_io = io.BytesIO()
        return gray_img

    def _topng(self,args):
        # load image
        img = cv2.imdecode(np.frombuffer(args[0].read(), np.uint8), 1)
        # convert to graky
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # threshold input image as mask
        mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)[1]
        # negate mask
        mask = 255 - mask
        # apply morphology to remove isolated extraneous noise
        # use borderconstant of black since foreground touches the edges
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        # anti-alias the mask -- blur then stretch
        # blur alpha channel
        mask = cv2.GaussianBlur(mask, (0,0), sigmaX=2, sigmaY=2, borderType = cv2.BORDER_DEFAULT)
        # linear stretch so that 127.5 goes to 0, but 255 stays 255
        mask = (2*(mask.astype(np.float32))-255.0).clip(0,255).astype(np.uint8)
        # put mask into alpha channel
        result = img.copy()
        result = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
        result[:, :, 3] = mask
        # save resulting masked image
        is_success,buffer = cv2.imencode(".png", result)
        byte_io = io.BytesIO(buffer)
        img = Image.open(byte_io)
        return img

    def _crop_ellipse(self,args):
        coord_x1,coord_y1,coord_x2,coord_y2,img = args
        img_rgba = Image.open(img).convert("RGBA")
        alpha_background = Image.new("L",img_rgba.size,color=0)
        draw = ImageDraw.Draw(alpha_background)
        draw.ellipse((coord_x1,coord_y1,coord_x2,coord_y2), fill=255)
        img_rgba.putalpha(alpha_background)
        im_rgba_crop = img_rgba.crop((coord_x1,coord_y1,coord_x2,coord_y2))
        return im_rgba_crop

    def _crop(self,args):
        coord_x1,coord_y1,coord_x2,coord_y2,img = args
        image = Image.open(img).convert("RGBA")
        res = image.crop((coord_x1,coord_y1,coord_x2,coord_y2))
        byte_io = io.BytesIO()
        return res

    def _paste(self,args):
        coord_x,coord_y,img1,img2 = args
        image1 = Image.open(img1).convert("RGBA")
        image2 = Image.open(img2).convert("RGBA")
        image1.paste(image2,(coord_x,coord_y),mask=image2)
        return image1

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
        return alpha_blended

    def _resize(self,args):
        img = args[1]
        width = args[0]
        image = Image.open(img)
        w,h = image.size
        ratio = h/w
        newsize = (width,int(width * ratio))
        new_image = image.resize(newsize)
        return new_image

    def _rotate(self,args):
        angle = args[0]
        img = args[1]
        image = Image.open(img).convert("RGBA")
        new_image = image.rotate(angle,expand=True,fillcolor=(0,0,0,0))
        return new_image

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

    async def run_image_processing(self,ctx,func,*args):
        t = functools.partial(func,args)
        m = await self.bot.loop.run_in_executor(None,t)
        bytes_io = io.BytesIO()
        m.save(bytes_io,"PNG")
        bytes_io.seek(0)
        f = discord.File(fp=bytes_io,filename="test.png")
        try:
            await ctx.send(content=f"Alright, {ctx.author.mention}, I'm done !",file=f)
        except discord.HTTPException as e:
            await ctx.send("File too large. I can't send this.")
        f.close()
        return

    @commands.command()
    async def resize(self,ctx,width:int,url:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
            return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._resize,width,img)
        return

    @commands.command()
    async def rotate(self,ctx,angle:int,url:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
            return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._rotate,angle,img)
        return
    
    @commands.command()
    async def blend(self,ctx,transparency:float,img1=None,img2=None):
        try:
            img1,img2 = await self.save_img(ctx.message,2)
        except TypeError:
            return await ctx.send("I need exactly two images to perform this command. Please, provide them. (upload one and give the discord image link for the other, or 2 discord image links).")
        f = await self.run_image_processing(ctx,self._blend,transparency,img1,img2)
        return
    
    @commands.command()
    async def paste(self,ctx,coord_x:int,coord_y:int,img1:str,img2:str=None):
        if coord_x < 0 or coord_y < 0:
            return await ctx.send("X and Y offset must be positive integers.")
        try:
            img1,img2 = await self.save_img(ctx.message,2)
        except TypeError:
            return await ctx.send("I need exactly two images to perform this command. Please, provide them. (upload one and give the discord image link for the other, or 2 discord image links).")
        f = await self.run_image_processing(ctx,self._paste,coord_x,coord_y,img1,img2)
        return
    
    @commands.group(invoke_without_command=True)
    async def crop(self,ctx,coord_x1:int,coord_y1:int,coord_x2:int,coord_y2:int,img:str=None):
        if ctx.invoked_subcommand is None:
            for i in [coord_x1,coord_x2,coord_y1,coord_y2]:
                if i < 0:
                    return await ctx.send("Only POSITIVES INTEGERS are allowed for this command.")
            try:
                img, = await self.save_img(ctx.message)
            except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
            f = await self.run_image_processing(ctx,self._crop,coord_x1,coord_y1,coord_x2,coord_y2,img)
            return

    @crop.command(invoke_without_command=True)
    async def ellipse(self,ctx,coord_x1:int,coord_y1:int,coord_x2:int,coord_y2:int,img:str=None):
        for i in [coord_x1,coord_x2,coord_y1,coord_y2]:
            if i < 0:
                return await ctx.send("Only POSITIVES INTEGERS are allowed for this command.")
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._crop_ellipse,coord_x1,coord_y1,coord_x2,coord_y2,img)
        return

    @commands.command()
    async def topng(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._topng,img)
        return

    @commands.group()
    async def filter(self,ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send("Subcommand required.")
    
    @filter.command()
    async def grayscale(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._grayscale,img)
        return

    @filter.command()
    async def invert(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._invert,img)
        return
    
    @filter.command()
    async def mirror(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._mirror,img)
        return
    
    @filter.command()
    async def posterize(self,ctx,number:int,img:str=None):
        if number > 8 or number < 1:
            return await ctx.send("I need a number between 1 and 8 !")
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._posterize,number,img)
        return

    @filter.command()
    async def solarize(self,ctx,number:int,img:str=None):
        if not (0 < number < 256):
            return await ctx.send("I need a number between 0 and 256 !")
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._solarize,number,img)
        return
    
    @filter.command()
    async def sepia(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._sepia,img)
        return

    @filter.command(aliases=["wb"])
    async def whiteblack(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._whiteblack,img)
        return

    @filter.command()
    async def swap1(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._swap1,img)
        return

    @filter.command()
    async def swap2(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._swap2,img)
        return

    @filter.command()
    async def swap3(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._swap3,img)
        return

    @filter.command()
    async def swap4(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._swap4,img)
        return

    @filter.command()
    async def swap5(self,ctx,img:str=None):
        try:
            img, = await self.save_img(ctx.message)
        except TypeError:
                return await ctx.send("I need exactly one image to perform this command. Please, provide it. (upload one or give the discord image link).")
        f = await self.run_image_processing(ctx,self._swap5,img)
        return
def setup(bot):
    bot.add_cog(ImageProcessing(bot))