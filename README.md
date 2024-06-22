# Google-gemini-discord-bot
A Python program that lets you use Google's Gemini API to create an interactive bot that can respond to text, images, audio, and videos for the platform 'discord'.

Currently, this version is made for personal use. 
~~The bot remembers the chat based on the user ID, this means you could continue the conversation between different servers and also edit the conversation in the log text file~~ (After the new version the chat history is saved as a pkl file) It can't be edit as of now.  

The "text" contains the text prompt entred by the user. It could be modified in the file directory: '/content/drive/MyDrive/Discord_bot/' [By default]. The "file_uri" contains the link for the media files that were uploaded during the chat sessions by using the files api. These files are deleted after 2 days, the max storage for ths 20 GB, while a single can't be bigger then 2GB. 

Now, that the logic has changed to handle the chat [26th May]version. It has now ganied the ability to have converstion history, even if a media file is uploaded; i.e. a video, audio, image, pdfs.  

~~Also, multiple users can't be in a single conversation as mentioned above the bot uses chat history to save a log file in the storage, and when a different persons responds(i.e. via replying to one of the bot responses or mentioning the bot.) It starts a new conversation with that user. ~~
Now it can have mutiple person in a channel in a server and support DM
I will try to add features and fix some bugs, as I learn more and do more experiments. 




# **HOW TO RUN**

1. Download the 'd_bot.ipynb' --> Open Google Colab --> [File --> Upload Notebook]
      Colab link = https://colab.research.google.com/drive/1OQGPc2CsYpnBhNfKEl0O0cDT6uXAcQ8g
   Or
Click on the "Run in colab" button.

2. Open it in Google Colab. And then press on the connect runtime. [Connect to the CPU runtime as we won't need any GPU juice for now]
3. Now mount your Google Drive to the runtime. (To do that, click on the leftmost menu after connecting to the runtime)
4. Now click on the bottom-most option that looks like a file. --> Click on the file with a Google Drive option on it.
    ![image](https://github.com/War004/Google-gemini-discord-bot/assets/138228378/a8cb7ce3-db44-4db0-bde0-7bfab1b2625f)
5. Now click on the 'key' looking option on the same left menu called "secrets"
6. Create two new keys with the names "DISCORD_TOKEN" and "GOOGLE_API_KEY", then type the value of the API in the values option.
   To get your Gemini API key, head to: "https://aistudio.google.com/" and sign in to your account, and click on Get API key.
   For getting your discord bot API key go to "https://discord.com/developers/docs/quick-start/getting-started" and create your application. Then go to the bot option from the left menu and click on reset token, after entering your password, you can copy the API key. (Remember to invite the bot with the correct permissions)
Now we are ready, just run all the cells one by one. From the top one.(It will require a restart after running the **Step 1: Install requirments **)
Any error will show up on the output cell.

# **HOW TO USE**
1. Simply tag the bot with your message or reply to it's one of the messages. Or you can dm the Bot. 
2. You could add attachments by just simply uploading them normally, just by using the '+' in Discord. [Currently the inbuilt gif won't work, gifs from windows work]
   **Now, you could also use links to attach a attachments; make sure that the link is targeted towards the file that you want to download.**
4. NOTE: The bot will only respond to the text to which it is tagged or if you reply to its messages, but in dm it will respond to every message. 
5. A red circle will show in the message which is being currently processed. When the red circle is shown it will not accpet any input from anyone.
   ~~6. If you are unhappy about a certain response, you can go to the log file where all the chats are saved for a particular user, based on user id and edit or remove the response according to your liking. ~~ (Temporary removed...)

# **Changes made**
1. Changed the internal logic for genrating responses.
2. Removed unnecessary functions [Less lines of codes compared to previous version]
3. Chat history for the chat having video file.
4. Added a command to see the token usage. (Use: Replay with "!check_token")
----22-06-2024
1. 

# **Errors**
Sometimes I would get the error: "User location is not supported for API use.". Details: "User location is not supported for the API use.", this could be fixed by disconnecting the runtime and connecting it again. [Not, noticed in a while]
If the user sends a gif through the inbuilt gif section, it's html page is downloaded
