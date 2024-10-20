# Google-gemini-discord-bot
A Python program that lets you use Google's Gemini API to create an interactive bot that can respond to text, images, audio, and videos on discord. 

Currently this version is made for personal use or with a small group of know (group of frineds/ small server or similar)

**Information on how it works**


A sample bot can be invited through this link: https://discord.com/oauth2/authorize?client_id=1228578114582482955&permissions=1689934876900416&integration_type=0&scope=bot (Permission required: manage webhooks)
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
There are two version for this application, one that can be run in the your local machine and other one in the google colab.
To run the local version:
1. First make sure python is installed in your machine, use "python/python3 --version" in your terminal in window. If it shows "Python {number}" It means python is installed. {If not installed download from microsoft store or the offical site https://www.python.org/downloads/ }
2. Then go inside the folder  "local Version" and then download the files, ".env", "local_Version.py", "requirments.txt", "utils.py" .
3. Keep all the folders in the same folder together.
4. Now open the folder in the windows explorer, and then look at the upper side in the windows explorer at the 'Address Bar' which would be showing text something like "This PC > Windows(C:)..."
5. Click on it and type cmd. The terminal will appear.
   1. Now we will make an virtual environment. Type the command: " python3 -m venv apikeys " the 'apikeys' is the name that you can change, for example you can use " python3 -m venv mouse ". But if you replace the name here be sure to change across where we will use it. (If you get some error during this step like moduel missing or somehting use pip install pip install virtualenv)
   2. After the completion for the above command, run the command to activate this: " apikeys\Scripts\activate.bat " {apikeys is the name be sure to change if you have a different name}
   3. After running the text in the terminal will change: " (apikeys) C:\.... " It means it is successfully activated.
   4. Now, we will run another command " pip install -U -r requirments.txt " it will show a bunch of things are getting installed, after the end of the installtion, minimize the termial for now.
   4.5 In the steps below you have open the .py files you can use any code editor or notepad.   
   5. Open the file " local_Version.py " and find the ' system_instruction ' under the " # Initial prompt " it would be followed by a '=' and the text '  Remember that you have the power of python to solve logical question if possible, don't forgot to try. When you the see the user message in the following format = ([string], [number]): {message content}. It means the conversation is happening in a server in discord. The string represents the username of the of the user who have sent the message and the number is the user id of the user.  Multiple people can interact during this, make sure too act accordingly. If you don't see this format and just see this format = (number) it means they are talking to you in dm, so act accordingly. ' Inside a tripe single quote. If you want the bot behave different differently you can change the string inside the triple single quote. Beware to keep the text inside the quotes!!
   6. Now below that in ' model_name ' you can put you preferred model. {models/gemini-1.0-pro-latest, models/gemini-1.0-pro, models/gemini-pro, models/gemini-1.0-pro-001, models/gemini-1.0-pro-vision-latest, models/gemini-pro-vision, models/gemini-1.5-pro-latest, models/gemini-1.5-pro-001, models/gemini-1.5-pro, models/gemini-1.5-pro-exp-0801, models/gemini-1.5-pro-exp-0827, models/gemini-1.5-flash-latest, models/gemini-1.5-flash-001, models/gemini-1.5-flash-001-tuning, models/gemini-1.5-flash, models/gemini-1.5-flash-exp-0827, models/gemini-1.5-flash-8b-exp-0827}.  Make sure put it inside the double quotes!!
   7. Now save the file.
   8. Now open ' .env ' file and replace the values for {DISCORD_TOKEN} and {GOGGLE_API_KEY} with the actual values. No need to put the values inside any quotes, just put the values after the '='
   9. Now save the file.
   10. Get back to the terminal and use the command ' python3/python public_version.py ' and it will start the bot.
   11. It's important to set the gemini api key through the command "set_api_key" even though you have gemini api key set in .env file.

To run in google colab:    
1. Once you have opened the notebook, run the cell called "Mount your google drive" after pressing it follow the scrren instructions until the cell has completed running. 
2. Now the run the cells in the order "Step 1: Install requirments (Restart)"[You have to restart the runtime after running it] --> "Step 2: Get the api key" --> "Model configuration" --> "Functions" --> "Running The Bot"
   * Note: to get the model_name you could run the cell "Step 2.5: List available models" and use the required model.
   * You can set system instructions as per as your needs, if you are leaving it empty it will show an error. Put a period "." in the system instruction if you are planning to not write anything in the system instructions.
     The default system instructions is:

           Remember that you have the power of python to solve logical question if possible, don't forgot to try. When you the see the user message in the following format = ([string], [number]): {message content}. It means the conversation is happening in a server in discord. The string represents the username of the of the user who have sent the message and the number is the user id of the user.  Multiple people can interact during this, make sure too act accordingly. If you don't see this format and just see this format = (number) it means they are talking to you in dm, so act accordingly. 

3. Now the bot should be running after running the cell "Running The Bot"  

**To know more about the bot you can refer to the document above**
