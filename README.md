# Google-gemini-discord-bot
A Python program that lets you use Google's Gemini API to create an interactive bot that can respond to text, image, audio, videos for the platform 'discord'.

Currently, this version is made for personal use.
The bot remembers the chat based on the user ID, this means you could continue the conversation between different servers and also edit the conversation in the log text file that is created. 
Also, multiple users can't be in a single conversation as mentioned above the bot uses chat history to save a log file in the storage, and when a different responds(i.e. via replying to one of the bot responses or mentioning the bot.) It start a new converstion with that user. 
And I will try to add features and fix some bugs, as I learn more and do more experiments. 


# **HOW TO RUN**

1. Open it in Google Colab. And then press on the connect runtime. [Connect to the CPU runtime as we won't need any GPU juice for now]
2. Now mount your Google Drive to the runtime. (To do that, click on the leftmost menu after connecting to the runtime)
3. Now click on the bottom-most option that looks like a file. --> Click on the file with a Google Drive option on it.
    ![image](https://github.com/War004/Google-gemini-discord-bot/assets/138228378/a8cb7ce3-db44-4db0-bde0-7bfab1b2625f)
4. Now click on the 'key' looking option on the same left menu called "secrets"
5. Create two new keys with the name "DISCORD_TOKEN" and "GOOGLE_API_KEY", then type the value of the api in the values option.
   For getting your gemini api key you can head to: "https://aistudio.google.com/" and sign in your account, and click on create on new api key.
   For getting your discord bot api key go to "https://discord.com/developers/docs/quick-start/getting-started" and create your application. Then goto the bot option from th left menu and click on reset token, after entering your password, you can copy the api key.(Remember to invite the bot with correct permsission)
Now we are ready, just run all the cells one by one. From the top one.
Any error will show up on the output cell.

**Errors**
Sometimes I would get the error:""User location is not supported for the API use.". Details: "User location is not supported for the API use.", this could be fixed by disconnecting the runtime and connecting it again
