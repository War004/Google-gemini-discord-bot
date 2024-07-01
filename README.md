# Google-gemini-discord-bot
A Python program that lets you use Google's Gemini API to create an interactive bot that can respond to text, images, audio, and videos on discord. 

Currently this version is made for personal use or with a small group of know (group of frineds/ small server or similar)

**Information on how it works**

* The bot uses google gemini api to produces responses.
* When a user initizes the bot(i.e. tagging/replying to the bot or sending DM) **his/her chatlogs is saved in the google drive of the person who is operating the bot**. The chat logs works to provide chat history for individual channel in a server or to individual user in a direct message. The chat log is saved in a pkl file type, so they are not directly editable which make the conversation non editable. 
* The chat logs have two parts; one is which stores the pure history in a pkl file; and second one which is a json file, used to store the files url for the attachments that are uploaded during the conversation.
* The default for the file directory are '/content/drive/MyDrive/Discord_bot/' for the pkl file and '/content/drive/MyDrive/Discord_bot/Time_files/' for the json file.
  The json file works to delete the files url after 48 hours, as it is the limit for the files api used in google gemini. Deleting the file url makes the attached message(if there were any messages attached to the 
  media file) while uploading the media to get deleted.
* The conversation happening in a channel can include mutiple user, to talk to the bot in a channel you have to reply to it's message or mention it and added your message with the mention.
  In direct messaging you don't have to do this, you can just simply send the messages and it would respond to each of the messages sent by you.

# **HOW TO RUN**
If you know about how to run a notebook in google colab and get the discord bot token and the google gemini api key you can stay here, for the people that don't know about it can go here to see detalied instructions:
https://docs.google.com/document/d/1JJ9JuE5aX2CHLASkVPg4yy0z2ENiI27dtgj8CBLIp0g/edit?usp=sharing
* If this is not working for some reason you can try going here:
      
      https://docs.google.com/document/d/e/2PACX-1vSX3RQo3GRmeD8XC_v5vBBGy4r312PvBITyneprB3kKs7_-p9wigeX-jjPGR-ASPJKWG4hDLR325XzR/pub

1. Once you have opened the notebook, run the cell called "Mount your google drive" after pressing it follow the scrren instructions until the cell has completed running. 
2. Now the run the cells in the order "Step 1: Install requirments (Restart)"[You have to restart the runtime after running it] --> "Step 2: Get the api key" --> "Model configuration" --> "Functions" --> "Running The Bot"
   * Note: to get the model_name you could run the cell "Step 2.5: List available models" and use the required model.
   * You can set system instructions as per as your needs, if you are leaving it empty it will show an error. Put a period "." in the system instruction if you are planning to not write anything in the system instructions.
     The default system instructions is:

           When you the see the user message in the following format = ([string], [number]): {message content}. It means the conversation is happening a server in discord. The string represents the username of the of the user who have sent the message and the number is the user id of the user.  Multiple people can interact during this, make sure too act accordingly. If you don't see this format and just see this format = (number) it means they are talking to you in dm, so act accordingly.

3. Now the bot should be running after running the cell "Running The Bot"  

**To know more about the bot you can refer to the document above**
