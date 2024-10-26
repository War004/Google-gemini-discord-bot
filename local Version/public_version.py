# local_Version.py
#source apikeys/bin/activate
# Import the Python SDK
import google.generativeai as genai
import os
import asyncio
import concurrent.futures
from dotenv import load_dotenv
from datetime import datetime, timezone
from utils import *
from slash_Commands import SlashCommandHandler
from log import stats_logging_task, write_bot_stats_to_file
load_dotenv()
# Used to securely store your API key
GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
api_key = GOOGLE_API_KEY
genai.configure(api_key=api_key)
api_keys = {}


# @title Step 2.5: List available models
"""for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)"""

print("Now select any one of the model and paste it in the 'model_name' below")

# Set the event listener for the dropdown change
# @title Model configuration
text_generation_config = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE"
  },
]

# Initial prompt
global system_instruction
system_instruction = """
Remember that you have the power of python to solve logical question if possible, don't forgot to try. When you the see the user message in the following format = ([string], [number]): {message content}. It means the conversation is happening in a server in discord. The string represents the username of the of the user who have sent the message and the number is the user id of the user.  Multiple people can interact during this, make sure too act accordingly. If you don't see this format and just see this format = (number) it means they are talking to you in dm, so act accordingly. 
"""
#models/gemini-1.5-flash-exp-0827
model_name = "models/gemini-1.5-flash-exp-0827" 
# Create the model using the selected model name from the dropdown
model = genai.GenerativeModel(model_name = model_name, generation_config=text_generation_config, system_instruction=system_instruction, safety_settings=safety_settings, tools="code_execution")

import re
import aiohttp
from typing import Final, Dict
import os
import discord
from discord import Intents, Client, Message, app_commands, WebhookMessage
from discord.ext import commands
import PIL.Image
from datetime import datetime
from google.ai.generativelanguage_v1beta.types import content
import google.generativeai as genai
import pytz
import asyncio
import io
import base64
from google.ai.generativelanguage_v1beta.types import content
import json

# STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
base_path = os.path.join(os.getcwd(), 'Discord_bot_files')

# Function to get the directory for a specific channel/DM
def get_channel_directory(message):
    if isinstance(message.channel, discord.DMChannel):
        server_id = "direct_Mess"
    else:
        server_id = str(message.guild.id)

    channel_id = str(message.channel.id)
    return os.path.join(base_path, server_id, channel_id)


# Function to get bot specific paths within a channel directory
def get_bot_paths(channel_dir, bot_id):
    bot_dir = os.path.join(channel_dir, bot_id)  # main_bot or webhooks
    os.makedirs(bot_dir, exist_ok=True)  # Ensure directory exists
    os.makedirs(os.path.join(bot_dir, "attachments"), exist_ok=True)

    chat_history_path = os.path.join(bot_dir, "chat_history.pkl")
    time_files_path = os.path.join(bot_dir, "time_files.json")
    attachments_dir = os.path.join(bot_dir, "attachments")
    return chat_history_path, time_files_path, attachments_dir

secondary_Prompt = """ You have power of python, slove any logical question/ maths question. Use python if someone is asking you a question which involves caluctions in the between or a logical question that you can use with it!!!"""

# STEP 1: BOT SETUP
intents: Intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, application_id=1228578114582482955)
processing_messages = {}
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
webhooks: Dict[int, discord.Webhook] = {}


def check_for_censorship(response):
  """
  Checks for censorship in the Gemini API response from chat.send_message.

  Args:
      response: The response object from chat.send_message.

  Returns:
      A tuple containing:
          - True if the response was censored, False otherwise.
          - The reason for censorship (if any).
  """
  candidates = response.get("candidates", [])
  if not candidates:
    return False, None  # No candidates generated, so no censorship

  # Check the first candidate (assuming you only want the top result)
  candidate = candidates[0]
  finish_reason = candidate.get("finish_reason")  # Note: 'finish_reason' instead of 'finishReason'
  safety_ratings = candidate.get("safety_ratings", [])

  if finish_reason == "SAFETY":
    # Censorship detected
    censorship_reasons = [
        f"{rating['category']}: {rating['probability']}" for rating in safety_ratings
    ]
    return True, ", ".join(censorship_reasons)

  return False, None


async def process_message(message: Message, is_webhook: bool = False) -> str:
    global chat_history, history
    utc_now = datetime.utcnow()
    spc_timezone = pytz.timezone('Asia/Tokyo')
    spc_now = utc_now.replace(tzinfo=pytz.utc).astimezone(spc_timezone)
    timestamp = spc_now.strftime('%Y-%m-%d %H:%M:%S')

    is_dm = isinstance(message.channel, discord.DMChannel)
    #id_str = str(message.author.id) if is_dm else str(message.channel.id)
    channel_dir = get_channel_directory(message)


    # Check if the message is a reply to another message
    if message.reference and message.reference.message_id and is_webhook:
        # Fetch the original message being replied to
        replied_message = await message.channel.fetch_message(message.reference.message_id)
        bot_id = str(replied_message.author.id)  # Use the replied-to user's ID
    else:
        bot_id = "main_bot"  # Fallback to the current message author's ID

    chat_history_path, time_files_path, attachments_dir = get_bot_paths(channel_dir, bot_id)


    username: str = str(message.author)
    user_message_with_timestamp = f"{timestamp} - ({username},[{message.author.id}]): {message.content}"
    channel_id = str(message.channel.id)
    print(channel_id)

    #print(f"({channel_dir}): {user_message_with_timestamp}") remove for  debugging
    result = await api_Checker(api_keys, channel_id)
    if not result:
        await message.channel.send("Please set up the API key. <https://aistudio.google.com/apikey>")
        await message.add_reaction('🔑')
        return
    api_key, model_name = result
    if not api_key:
        await message.channel.send("Please set up the API key. <https://aistudio.google.com/apikey>")
        await message.add_reaction('🔑')
        return
    #print(api_key)
    #print(model_name)
    genai.configure(api_key=api_key)
    if is_webhook:
        webhook_instruction = load_webhook_system_instruction(bot_id, channel_dir)
        custom_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=text_generation_config,
            system_instruction=webhook_instruction,
            safety_settings=safety_settings,
            tools="code_execution"
        )
    else:
        custom_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=text_generation_config,
            system_instruction=system_instruction,
            safety_settings=safety_settings,
            tools="code_execution"
        )

    history = load_chat_history(chat_history_path)
    chat_history = check_expired_files(time_files_path, history)
    chat = custom_model.start_chat(history=chat_history)

    url_pattern = re.compile(r'(https?://[^\s]+)')
    urls = url_pattern.findall(message.content)
    Direct_upload = False
    Link_upload = False
    attach_url = None

    if urls:
        attach_url = urls[0]
        Link_upload = True

    if message.attachments:
        for attachment in message.attachments:
            attach_url = attachment.url
            Direct_upload = True
            break

    try:
        if Direct_upload or Link_upload:
            loop = asyncio.get_running_loop()
            format, downloaded_file = await loop.run_in_executor(
                thread_pool, download_file, attach_url, attachments_dir
            ) # updated

            if format and downloaded_file:
                if format in ('image/gif'):
                    gif_clip = mp.VideoFileClip(downloaded_file)
                    output_path = f"{downloaded_file.rsplit('.', 1)[0]}.mp4"
                    gif_clip.write_videofile(output_path, codec='libx264')
                    downloaded_file = output_path
                    format = 'video/mp4'

                media_file = [upload_to_gemini(f"{downloaded_file}", mime_type=f"{format}"), ]

                wait_for_files_active(media_file)

                save_filetwo(time_files_path, media_file[0].uri) # updated

                response = await chat.send_message_async([user_message_with_timestamp, media_file[0]])
                response = response.text

                save_chat_history(chat_history_path, chat) # updated
                #print(f"Bot: {response}") #remove for  debugging
                Direct_upload = False
                Link_upload = False

                return response

            if format is None and downloaded_file:
                response = f"File too big. Max size: {downloaded_file}GB"
            else:
                response = "Something werid happened."
        

        else:
            response = await chat.send_message_async(user_message_with_timestamp)
            response = response.text
            save_chat_history(chat_history_path, chat) # updated
            #print(f"Bot: {response}") remove for  debugging

        return response

    except GoogleAPIError as e:
        error_message = await error_handler.handle_error(message, e, channel_dir) # updated
        return error_message


@bot.event
async def on_message(message: Message) -> None:
    if message.author == bot.user:  # Ignore messages from the bot itself
        return

    is_webhook_interaction = False
    webhook = None

    try:
        # Check if the message is a reply to a webhook
        if message.reference:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message.webhook_id:
                webhook = await bot.fetch_webhook(referenced_message.webhook_id)
                is_webhook_interaction = True

        if is_webhook_interaction and webhook:  # Handle webhook interactions
            if message.id in processing_messages:
                return # Already processing
            processing_messages[message.id] = True 

            asyncio.create_task(handle_message(message, webhook=webhook)) # Use create_task

        # Check if the message mentions the bot or is a DM, ONLY if not a webhook interaction
        elif (bot.user in message.mentions or isinstance(message.channel, discord.DMChannel)) and not is_webhook_interaction:
            if message.id in processing_messages:
                return # Already processing
            processing_messages[message.id] = True

            asyncio.create_task(handle_message(message))  # Use create_task
        
        # Process other bot commands (if any) - likely not needed if all handled by slash commands now
        await bot.process_commands(message) # KEEP THIS for any prefix-based commands that remain.

    except discord.NotFound:
        print(f"Webhook or message not found for message {message.id}")
    except discord.Forbidden:
        print(f"Bot doesn't have permission to interact with webhook for message {message.id}")
    except Exception as e:
        print(f"Error processing message {message.id}: {str(e)}")

async def handle_message(message, webhook=None):
    try:
        await message.add_reaction('\U0001F534')
        response = await process_message(message, is_webhook=bool(webhook)) # Pass webhook info

        if webhook: # Use the correct send_message function
            await send_message_webhook(webhook=webhook, response=response)
        else:
            await send_message_main_bot(message=message, response=response)

    except discord.NotFound:
        print(f"Message not found: {message.id}")  # Handle message not found (e.g., deleted during processing)
    except Exception as e:
        print(f"Error in handle_message: {e}")  # More general error handling
    finally:
        await message.remove_reaction('\U0001F534', bot.user)
        if message.id in processing_messages: #Cleanup the processing messages dict
            del processing_messages[message.id]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    #bot.loop.create_task(stats_logging_task())
    global api_keys
    api_keys = await load_api_keys()


    slash_handler = SlashCommandHandler(
        bot=bot,
        model=model,
        model_name=model_name,
        text_generation_config=text_generation_config,
        system_instruction=system_instruction,
        safety_settings=safety_settings,
        webhooks=webhooks,
        api_keys = api_keys,
        GOOGLE_API_KEY = GOOGLE_API_KEY,
        get_channel_directory=get_channel_directory,
        get_bot_paths=get_bot_paths,
        load_chat_history=load_chat_history,
        save_chat_history=save_chat_history,
        check_expired_files=check_expired_files,
        load_webhook_system_instruction=load_webhook_system_instruction,
        send_message_webhook=send_message_webhook,
    )
    # Load existing webhook data from new directory structure
    await load_webhooks_from_disk(bot, base_path, webhooks)

    #command for apikeys
    @bot.tree.command(name="set_api_key", description="Set your Google API key for this channel")
    @app_commands.describe(api_key="Your Google API key")
    async def set_api_key_command(interaction: discord.Interaction, api_key: str):
        await interaction.response.defer(ephemeral=True)  # Respond privately
        try:
            
            # Validate the API key  not working
            genai.configure(api_key=api_key)  # Test the key
            #response = model.generate_content("Write hello world")

            # Store the API key for the channel
            channel_id = str(interaction.channel.id)
            if channel_id in api_keys:
                    # Only update the model_name, leave the api_key unchanged
                    api_keys[channel_id]["api_key"] = api_key
            else:
                # If the channel_id does not exist, create a new entry with just the model_name
                # Optionally: Set a default api_key if needed
                api_keys[channel_id] = {
                    "api_key": api_key,  
                    "model_name": None # Replace this or leave it if API key is managed elsewhere
                }
            
            # Save the updated api_keys dictionary
            await save_api_json(api_keys)
            await interaction.followup.send("API key set successfully!\n⚠️If you have previosuly uploaded any media files during the current session, then if you try to resume these chats you will get error: You do not have permission to access the File ---------- or it may not exist. To reslove you should use your old api key.(or wait for 48 hours, as attachemnts are removed after 48 hours from the chats memory.)", ephemeral=True)

        except GoogleAPIError as e:
            await interaction.followup.send(f"{e}", ephemeral=True)

    await slash_handler.setup_slash_commands()
    await bot.tree.sync()

# STEP 5: MAIN ENTRY POINT
def main():
    bot.run(TOKEN)

if __name__ == "__main__":
    main()