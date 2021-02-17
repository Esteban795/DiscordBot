# DiscordBot

Welcome to my first Discord Bot ! Here you can find the source code I've written. This is still a beta version of this bot, so make sure to report any bug that you encounter !

## **The bot prefix is : $. I don't plan on changing it, but I will edit this line if it ever happens !**

# What this bot can do :

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

He will answer : 

```txt
Hello [Guild name of the person who sent the message]
```

That's all for now, I'm working on implementing a way for anyone to add customized words/sentences that will trigger the bot into saying something too !

# Now the commands !

- $echo : just repeats whatever you say. It won't trigger a command if you type *$echo $[another command]*

Example : 

> $echo Hi, I'm ChuckNorris
> Bot : Hi, I'm ChuckNorris

