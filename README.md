# DiscordBot

Welcome to my first Discord Bot ! Here you can find the source code I've written. This is still a beta version of this bot, so make sure to report any bug that you encounter !


### Requirements

- This bot needs you to first install discord.py :

For a basic installation :

```ps
py -3 -m pip install -U discord.py
```
If you also want voice support : 

```ps
python3 -m pip install -U discord.py[voice]
```

- This bot requires you to have a bot token stored in a .env file. It should look like :

```txt
BOT_TOKEN = [your bot token]
```

- You also may need to install the "requests" library if you didn't use it before !

```ps
python3 -m pip install -U request.py
```

### **The bot prefix is : $. I don't plan on changing it, but I will edit this line if it ever happens !**




## What this bot can do :

### Logs system.
***********************************************************************************
***The bot will automatically create a file named "logs.txt" in the same directory where the file "bot.py" is.***

The log format is : 

```txt
[time (UTC) the message was sent] ||||| Message from [the user who sent the message : [the content of the message]
```

You will for the moment need to open the file by yourself to see the logs. I'm working on a
way to go through the logs depending on the name of the author, and it will came out as soon as I can.

# Basic interactions

- For now, the bot only answers people saying 
```py
["hello",'hi','greetings','greet','hi there']
```

- He will answer : 

```txt
Hello [Guild name of the person who sent the message] !
```

That's all for now, I'm working on implementing a way for anyone to add customized words/sentences that will trigger the bot into saying something too !

# Now the commands !

- $echo : just repeats whatever you say. It won't trigger a command if you type *$echo $[another command]*

Example : 

```txt
$echo Hi, I'm ChuckNorris
```

```txt
ChuckNorrisBot : Hi, I'm ChuckNorris
```

**This command requires no permissions.**

***********

- $giverole : will give the role to the tagged member.

Example : 

> $giverole @ThatOneGuy demi-god

The guild member with name "ThatOneGuy" will be granted the "demi-god" role if it exists ! (Working on error handling if the role doesn't exist. I'm looking for a way to auto-create the role if there isn't one.)





- $removerole : will remove the specified role from the tagged member.

Example : 

> $removerole @ThatOneGuyAgain demi-god

The guild member "ThatOneGuyAgain" will see this awesome role taken from him (if he currently has it of course).

**Both of these commands require you to have the permission to manage roles on the guild you use the bot.**

**************

- $kick : will kick the specified member from the server. Also sends the kicked member the following message :
*You were kicked from [server they got kicked] by [the person who kicked them] for : [reasons, "Not specified" if there are no reasons that were written]

Example : 

> $kick @ThatOneGuyAgainAndAgain trolling

- @ThatOneGuyAgainAndAgain gets kicked out of the guild.

> @ThatOneGuyAgainAndAgain gets a DM.
> You were kicked from TheBestGuildEver by TheBestModerator for : trolling.


**This command requires that you have the "Kick Members" permission !**


**************

- $purge : will delete a specified amout of messages from the online chat. If nothing is specified, it will only delete the last 2 messages !

Example : 

> $purge 1000

This will delete the last 1000 messages from the chat (if there are 1000 or more. If there are only 500 messages, the bot won't obviously delete more than 500 messages.)

**This command requires that you have the "Manage messages" permission !**


*************

- $banlist : this command will show you the current banlist of the guild. If no one is banned, the bot will answer a kind message !

Examples : 

- ThatOneGuy#5555 is banned.

> $banlist

```txt
Ban list: 
• ThatOneGuy#5555 for : [the reason he was banned]
```


- No one is banned.

> $banlist

```txt
Uh oh. Looks like no one is currently banned on this server ! Keep it up.
```

**This command requires that you have the "Administrator" permission !**


**************************

- $perms : will send you in DM the permissions that the tagged user have.

Example : 
> $perms @ThatOneGuy 

- in DM :
```txt
Administrator : False
Manage messages : True
...
```

**This command requires that you have the "Administrator" permission!**

*********

- $unban : this command allows you to unban a user from your guild.

I will need to develop that command since it's a bit complex.

```txt
$unban
```
You always need to specify the name of the person you would like to unban. Not giving the bot a name will only return :

```txt
You need to tell me who I need to unban !
```

##### Then there are 2 cases :

- First, the current guild has no banned members. Then the bot will just say that no one is currently banned, and so there is no one to unban.

```txt
$unban ThatOneGuy#5555
```

```txt
Uh oh. Looks like no one is currently banned on this server ! Keep it up.
```



##### Second case, the guild does have banned members. Then there are 2 mores cases !

- 