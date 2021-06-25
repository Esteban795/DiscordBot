import discord
from discord.ext import commands
import aiohttp
import re

class Reddit(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    def create_reddit_embed(self,data:dict):
        """
        Parameters : data, a dict with Reddit API informations
        Return : a discord.Embed object, filled with every infos about this post 
        (title, author,subreddit upvotes,number of comments)
        """
        youtube_video_link = re.compile(r"(https://www.youtube.com/watch|https://clips.twitch.tv/|https://reddit.com/link/o4v2hm/video/|https://www.twitch.tv/(?:\w{0,255})/clip)")
        author = data["author"]
        print(f"Author : {author}")
        num_comments = data.get("num_comments")
        content = data["selftext"]
        img_url = data["url"]
        is_video_link = youtube_video_link.findall(img_url)
        is_video = data["is_video"]
        if is_video_link:
            print("lien détecté")
            is_video = True
        title = f'{data["subreddit_name_prefixed"]} - Post by u/{author}\n\n{data["title"]}'
        link = f"https://www.reddit.com{data['permalink']}"
        meme_embed = discord.Embed(olor=0xff0000)
        meme_embed.set_author(name=title,url=link)
        meme_embed.set_footer(text=f"▲ {data['ups']} | ✉ {num_comments}")
        if content:
            meme_embed.description = content if len(content) < 250 else content[:250] + "..."
        if is_video:
            meme_embed.description = "This is a video, so you can't play it through an embed !"
        else:
            meme_embed.set_image(url=img_url)
        return meme_embed

    @commands.group()
    async def reddit(self,ctx:commands.Context,subreddit:str="meme",number:int=1):
        """
        This command is a group. When passed with no subcommands, it does the following stuff :

        1) Fetch (a) random post(s)  (depending on ``number`` variable) from the Reddit API (Default value for the subreddit is r/meme)
        2) Depending on subreddits, the API response is a list or a dict, but both contains the same
        informations. If the response is a list, I only use the first indexed element, which is the 
        random post.
        3) I pass the informations into a function that returns an embed.
        """
        if ctx.invoked_subcommand is None:
            for i in range(number):
                url = f'https://www.reddit.com/r/{subreddit}/random.json'
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(url) as r:
                        res = await r.json()
                if isinstance(res,list):
                    data = res[0]["data"]["children"][0]["data"]
                else:
                    data = res["data"]["children"][0]["data"]
                post = self.create_reddit_embed(data)
                await ctx.send(embed=post)

def setup(bot):
    bot.add_cog(Reddit(bot))