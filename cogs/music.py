import discord
from discord.ext import commands
import youtube_dl
from bot import ydl_opts

class Music(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    def already_connected_or_playing(self,c:commands.Context):
        return (c.voice_client is None or c.voice_client.is_playing() is False) and c.author.voice is not None
            
    @commands.command(aliases=["song"])
    async def play(self,ctx,url:str):
        if self.already_connected_or_playing(ctx):
            channel = ctx.author.voice.channel
            await channel.connect()
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                song_info = ydl.extract_info(url, download=False)
            embedVar = discord.Embed(title="Now playing...",color=0xaaaaff,description=song_info["title"])
            await ctx.send(embed=embedVar)
            ctx.guild.voice_client.play(discord.FFmpegPCMAudio(song_info["formats"][0]["url"]))
            ctx.guild.voice_client.source = discord.PCMVolumeTransformer(ctx.guild.voice_client.source)
            ctx.guild.voice_client.source.volume = 1
        else:
            await ctx.message.delete()
            embedVar = discord.Embed(title="Uh oh. Something went wrong.",color=0xff0000,description="I can't be in two voice channels at the same time. Please wait until I'm available !")
            await ctx.send(embed=embedVar)

    @commands.command(aliases=["disconnect"])
    async def leave(self,ctx):
        await ctx.voice_client.disconnect()
    
    @commands.command()
    async def pause(self,ctx):
        await ctx.voice_client.pause()
    
    @commands.command()
    async def resume(self,ctx):
        await ctx.voice_client.resume()

    @commands.command()
    async def stop(self,ctx):
        ctx.voice_client.stop()

def setup(bot):
    bot.add_cog(Music(bot))