import discord
from discord.ext import commands
import aiohttp
import re

class Reddit(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.post_type = {"reddit":"https://www.reddit.com/r/{}/random.json?limit=1",
        "rising":"https://www.reddit.com/r/{}/rising.json?limit=1",
        "new":"https://www.reddit.com/r/{}/new.json?limit=1",
        "controversial":"https://www.reddit.com/r/{}/controversial.json?limit=1",
        "top":"https://www.reddit.com/r/{}/top.json?limit=1"} #Will be used to get URL for each command

    async def reddit_request(self,ctx:commands.Context,url:str,subreddit:str):
        """
        Make a request to reddit API.

        ### Parameters :
        - ctx : Required in case subreddit doesn't exist to alert the channel the bot couldn't find what they are looking for. Will be passed in the self.create_reddit_embed method to allow sending the rich embed.
        - url : a URL that comes from self.post_type dict. This URL will be used to make the API request.
        - subreddit : the subreddit's name. Examples : meme,france etc.

        ### Raises :
        - Nothing should be raised by this method if parameters are correct.

        ### Returns :
        - If the request went ok, then this method calls another method to build the discord.Embed object.
        """
        async with aiohttp.ClientSession() as cs: #Async GET request
            async with cs.get(url.format(subreddit)) as r:
                res = await r.json()
            if isinstance(res,list): #Sometimes, API returns a list sometimes a dict. I'm checking which one each calls
                if not res[0]["data"]["dist"] or res[0].get("error"): #Check if any post could be found
                    return await ctx.send("Couldn't find any posts on this subreddit. Try a valid name !")
                post_data = res[0]["data"]["children"][0]["data"] #
            else:
                if not res["data"]["dist"] or res.get("error"):
                    return await ctx.send("Couldn't find any posts on this subreddit. Try a valid name !")
                post_data = res["data"]["children"][0]["data"]
        return await self.create_reddit_embed(ctx,post_data)

    async def create_reddit_embed(self,ctx,data:dict):
        """
        ### Parameters : 
        - data, a dict with Reddit API informations

        ###Returns : 
        - a discord.Embed object, filled with every infos about this post 
        (title, author,subreddit upvotes,number of comments)
        """
        youtube_video_link_regex = re.compile(r"(https://www.youtube.com/watch|https://clips.twitch.tv/|https://reddit.com/link/o4v2hm/video/|https://www.twitch.tv/(?:\w{0,255})/clip)") #Any link that looks like this ? It's a video then, and can't play it throuh embed
        author = data["author"]
        num_comments = data.get("num_comments")
        content = data["selftext"]
        img_url = data["url"]
        is_video_link = youtube_video_link_regex.findall(img_url) #check for videos link
        is_video = data["is_video"]
        if is_video_link:
            is_video = True
        title = f'{data["subreddit_name_prefixed"]} - Post by u/{author}\n\n{data["title"]}' #From there, just embed building
        link = f"https://www.reddit.com{data['permalink']}"
        meme_embed = discord.Embed(olor=0xff0000)
        meme_embed.set_author(name=title,url=link)
        meme_embed.set_footer(text=f"{data['ups']} upvotes | {num_comments} comments.")
        if content:
            meme_embed.description = content if len(content) < 250 else content[:250] + "..."
        if is_video:
            meme_embed.description = "This is a video, so you can't play it through an embed !"
        else:
            meme_embed.set_image(url=img_url)
        await ctx.send(embed=meme_embed)

    @commands.group(invoke_without_command=True)
    async def reddit(self,ctx:commands.Context,subreddit:str="meme"):
        """
        This command is a group. When passed with no subcommands, it does the following stuff :

        1) Fetch a random post from the Reddit API (Default value for the subreddit is r/meme)
        2) Depending on subreddits, the API response is a list or a dict, but both contains the same
        informations. If the response is a list, I only use the first indexed element, which is the 
        random post.
        3) I pass the informations into a function that returns an embed.
        """
        if ctx.invoked_subcommand is None:
            url = self.post_type[ctx.invoked_with] #Get the right URL according to the command used
            await self.reddit_request(ctx,url,subreddit) #API request

    @reddit.command()
    async def rising(self,ctx,subreddit:str="meme"):
        url = self.post_type[ctx.invoked_with] #Get the URL we're gonna use
        await self.reddit_request(ctx,url,subreddit) #API request
    
    @reddit.command()
    async def new(self,ctx,subreddit:str="meme"):
        url = self.post_type[ctx.invoked_with]
        await self.reddit_request(ctx,url,subreddit) #API request
    
    @reddit.command()
    async def controversial(self,ctx,subreddit:str="meme"):
        url = self.post_type[ctx.invoked_with]
        await self.reddit_request(ctx,url,subreddit) #API request

    @reddit.command()
    async def top(self,ctx,subreddit:str="meme"):
        url = self.post_type[ctx.invoked_with]
        await self.reddit_request(ctx,url,subreddit) #API request
    
def setup(bot):
    bot.add_cog(Reddit(bot))