# Import the Python SDK
from google import genai
from google.genai import types
import sys
import traceback
import os
import asyncio
import concurrent.futures
from dotenv import load_dotenv
from datetime import datetime, timezone
from utilsNew import *
from slash_CommandsNew import SlashCommandHandler
import re
import aiohttp
from typing import Final, Dict
import discord
from discord import Intents, Client, Message, app_commands, WebhookMessage
from discord.ext import commands
import PIL.Image
import pytz
import io
import base64
import json

load_dotenv()

# Used to securely store your API key
GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
api_key = GOOGLE_API_KEY
client = genai.Client(api_key=GOOGLE_API_KEY)
api_keys = {}

#Json files for languages
with open("enString.json", "r") as file:
    en = json.load(file) #English
with open("asString.json", "r") as file:
    asS = json.load(file) #Assamese
with open("bnString.json", "r") as file:
    bn = json.load(file) #Bengali
with open("guString.json", "r") as file:
    gu = json.load(file) #Gujarati
with open("hiString.json", "r") as file:
    hi = json.load(file) #Hindi
with open("knString.json", "r") as file:
    kn = json.load(file) #Kannada
with open("maiString.json", "r") as file:
    mai = json.load(file) #Maithili
with open("malString.json", "r") as file:
    mal = json.load(file) #Malayalam
with open("mniString.json", "r") as file:
    mni = json.load(file) #Meitei
with open("mrString.json", "r") as file:
    mr = json.load(file) #Marathi
with open("neString.json", "r") as file:
    ne = json.load(file) #Nepali
with open("taString.json", "r") as file:
    ta = json.load(file) #Tamil
with open("ruString.json", "r") as file:
    ru = json.load(file) #Russian
with open("jaString.json", "r") as file:
    ja = json.load(file) #Japanese
with open("frString.json", "r") as file:
    fr = json.load(file) #French

def get_language_dict(language_code):
    """
    Returns the appropriate language dictionary based on the language code.

    Args:
        language_code (str): The language code (e.g., "en", "asS", "bn").

    Returns:
        dict: The corresponding language dictionary, or the English dictionary as a default.
    """
    language_map = {
        "en": en,
        "asS": asS,
        "bn": bn,
        "gu": gu,
        "hi": hi,
        "kn": kn,
        "mai": mai,
        "mal": mal,
        "mni": mni,
        "mr": mr,
        "ne": ne,
        "ta": ta,
        "ru": ru,
        "ja": ja,
        "fr": fr,
        # ... add other mappings
    }
    return language_map.get(language_code, en)  # Default to English if not found

language_name ={
        "en": "English",
        "asS": "Assamese",
        "bn": "Bengali",
        "gu": "Gujarati",
        "hi": "Hindi",
        "kn": "Kannada",
        "mai": "Maithili",
        "mal": "Malayalam",
        "mni": "Meitei",
        "mr": "Marathi",
        "ne": "Nepali",
        "ta": "Tamil",
        "ru": "Russian",
        "ja": "Japanese",
        "fr": "French"
    }
# Initial prompt
#removed temporary Remember that you have the power of python to solve logical questions if possible. 
global system_instruction
system_instruction = """

"""

#insert the config parameters here!!
#stop_sequences=["STOP!"]
config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=1,
    top_p=0.95,
    top_k=40,
    candidate_count=1,
    seed=-1,
    max_output_tokens=8192,
    #presence_penalty=0.5,
    #frequency_penalty=0.7, Removed this till gemini 2.0 pro doesn't come out
    safety_settings=[
        types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
        types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
        types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
        types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE')
    ],
)
"""
tools=[
        types.Tool(code_execution={}),
    ]
"""

model_name = "models/gemini-2.0-flash" 

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
bot = commands.Bot(command_prefix='!', intents=intents, application_id=1228578114582482955) # Replace with your application ID
processing_messages = {}
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
webhooks: Dict[int, discord.Webhook] = {}
bot_webhook_ids = set()  # Initialize an empty set to store your bot's webhook IDs


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
    lan = en
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
    #print(channel_id)

    #print(f"({channel_dir}): {user_message_with_timestamp}") remove for  debugging
    result = await api_Checker(api_keys, channel_id)
    if not result:
        await message.channel.send(lan["noInfomation"])
        await message.add_reaction('🔑')
        return
    api_key, model_name, laCode = result
    if not api_key:
        await message.channel.send(lan["noInfomation"])
        await message.add_reaction('🔑')
        return
    #print(api_key)
    #print(model_name)
    #print(laCode)
    if laCode is None:
        laCode = "en"
    lan = laCode
    lan = get_language_dict(lan)
    client = genai.Client(api_key=api_key)
    history = load_chat_history(chat_history_path)
    chat_history = await check_expired_files(time_files_path, history, chat_history_path)

    with open(chat_history_path, 'wb') as file:
        pickle.dump(chat_history, file)

    if is_webhook:
        webhook_instruction = load_webhook_system_instruction(bot_id, channel_dir)
        if model_name == "models/gemini-2.0-flash-exp":
            blockValue = "OFF"
        else:
            blockValue = "BLOCK_NONE"
        if model_name == "models/gemini-2.0-flash-thinking-exp-01-21":
            ouputToken = 65536
        else:
            ouputToken = 8192
        chat = client.aio.chats.create(
            model=model_name,
            config = types.GenerateContentConfig(
                system_instruction=webhook_instruction,
                temperature=1,
                top_p=0.95,
                top_k=20,
                candidate_count=1,
                seed=-1,
                max_output_tokens=ouputToken,
                #presence_penalty=0.5,
                #frequency_penalty=0.7, Removed this till gemini 2.0 pro doesn't come out
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold=blockValue),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold=blockValue),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold=blockValue),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold=blockValue)
                ],
                tools=[
                    types.Tool(code_execution={}),
                ]
            ),
            history=chat_history,
        )
        #old sdk
        """custom_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=text_generation_config,
            system_instruction=webhook_instruction,
            safety_settings=safety_settings,
            tools="code_execution"
        )"""
    else:
        if model_name == "models/gemini-2.0-flash-thinking-exp-01-21":
            new_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=1,
                top_p=0.95,
                top_k=40,
                candidate_count=1,
                seed=-1,
                max_output_tokens=65536,
                #presence_penalty=0.5,
                #frequency_penalty=0.7, Removed this till gemini 2.0 pro doesn't come out
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE')
                ],
                tools=[
                    types.Tool(code_execution={}),
                ]
            )
            chat = client.aio.chats.create(
                model=model_name,
                config=new_config,
                history=chat_history,
            )
        if model_name == "models/gemini-2.0-flash-lite-preview-02-05":
            new_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=1,
                top_p=0.95,
                top_k=40,
                candidate_count=1,
                seed=-1,
                max_output_tokens=8192,
                #presence_penalty=0.5,
                #frequency_penalty=0.7, Removed this till gemini 2.0 pro doesn't come out
                safety_settings=[
                    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE')
                ]
            )
            chat = client.aio.chats.create(
                model=model_name,
                config=new_config,
                history=chat_history,
            )
        else:
            chat = client.aio.chats.create(
                model=model_name,
                config=config,
                history=chat_history,
            )
        #old sdk
        """custom_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=text_generation_config,
                system_instruction=system_instruction,
                safety_settings=safety_settings,
                tools="code_execution
        )"""
        """
        if (model_name == "models/gemini-2.0-flash-exp"):
            print("Hello")
            custom_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=text_generation_config,
                system_instruction=system_instruction,
                safety_settings=safety_settings,
                tools={
                    "google_search_retrieval": {
                        "dynamic_retrieval_config": {
                            "mode": "unspecified",
                            "dynamic_threshold": 0.3
                        }
                    },
                    "code_execution": {}
                }
            )
        else:
            custom_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=text_generation_config,
                system_instruction=system_instruction,
                safety_settings=safety_settings,
                tools="code_execution"
            )"""

    # Check if the message is in a guild (server) or DM
    if message.guild:  # If message is in a server
        if message.mentions and message.guild.me in message.mentions and not message.reference:
            user_message_with_timestamp = await handle_tagged_message(message,lan)
        else:
            username: str = str(message.author)
            user_message_with_timestamp = f"{timestamp} - ({username},[{message.author.id}]): {message.content}"
    else:  # If message is in DMs
        username: str = str(message.author)
        user_message_with_timestamp = f"{timestamp} - ({username},[{message.author.id}]): {message.content}"
    
    print(user_message_with_timestamp)

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
            message_index = len(chat_history)
            loop = asyncio.get_running_loop()
            format, downloaded_file = await loop.run_in_executor(
                thread_pool, download_file, attach_url, attachments_dir
            )

            if format and downloaded_file:
                
                if format.startswith('video/'):
                    # Extract audio
                    audio_output_path = f"{downloaded_file.rsplit('.', 1)[0]}_audio.mp3"  #Output path for audio file 
                    print(audio_output_path)
                    print("--------------")
                    audio_file_path = await extract_audio(downloaded_file, audio_output_path)
                    audio_format = determine_file_type(audio_file_path)
                    
                    if audio_format is None:
                        ifAudio = lan["promptIfAudioNone"]

                    if audio_format:
                        file = await client.aio.files.upload(file=audio_file_path, config=types.UploadFileConfig(mime_type=audio_format))
                        file_uri = file.uri  # Get the URI from the media_file object
                        mime_type = file.mime_type  # Get the mime_type from the media_file object
                        media_file = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

                        status = await wait_for_file_activation(name=file.name,client=client)

                        if not status:
                            response = lan["errorVideoinAudioActivation"]
                            return response

                        print("Going to do the processing of the audio file!")

                        save_filetwo(time_files_path, file_uri, message_index)
                        response = None
                        response = await chat.send_message([lan["promptDuringAudio"], media_file])
                        response = await extract_response_text(response)
                        save_chat_history(chat_history_path, chat)
                        os.remove(audio_output_path) # deleting audio file after sending it to gemini
                        print("The audio file has been processed")
                        ifAudio = lan["ifAudio"]

                    # Sending video file
                    file = await client.aio.files.upload(file=downloaded_file, config=types.UploadFileConfig(mime_type=format))
                    file_uri = file.uri  # Get the URI from the media_file object
                    mime_type = file.mime_type  # Get the mime_type from the media_file object
                    media_file = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

                    status = await wait_for_file_activation(name=file.name,client=client)

                    if not status:
                        response = lan["errorVideoinVideoActivation"]
                        return response


                    print("Going to do the processing of the video file!")

                    response = await chat.send_message([f"{ifAudio} {user_message_with_timestamp}", media_file])
                    if(response):
                        save_filetwo(time_files_path, file_uri, (message_index + 2)) #2= 1st len from the audio file + model response
                        response = await extract_response_text(response)
                        save_chat_history(chat_history_path, chat)
                        Direct_upload = False
                        Link_upload = False
                        return response
                    else:
                        response = lan["errorWhileUploading"]

                        return response
                if format.startswith('image/'):
                    if format == 'image/gif':
                        model_used = chat._model
                        if(model_used == "models/gemini-2.0-flash-exp"):
                            pass
                        else:
                            gif_clip = mp.VideoFileClip(downloaded_file)
                            output_path = f"{downloaded_file.rsplit('.', 1)[0]}.mp4"
                            gif_clip.write_videofile(output_path, codec='libx264')
                            downloaded_file = output_path
                            format = 'video/mp4'
                    """else:
                        response = lan["restirctionStillImage"]
                        return response"""


                file = await client.aio.files.upload(file=downloaded_file, config=types.UploadFileConfig(mime_type=format))
                file_uri = file.uri  # Get the URI from the media_file object
                mime_type = file.mime_type  # Get the mime_type from the media_file object
                media_file = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)

                status = await wait_for_file_activation(name=file.name,client=client)
                if not status:
                    response = lan["errorNormalMediaActivation"]
                    return response

                save_filetwo(time_files_path, file_uri, message_index)

                response = await chat.send_message([f"Do the conversation follwoing language code: ||{lan}||. The user message = {user_message_with_timestamp} {lan['promptDuringMedia']}", media_file])

                
                response = await extract_response_text(response)

                #print(f"Actual response: after extract_response {response}")

                save_chat_history(chat_history_path, chat)
                Direct_upload = False
                Link_upload = False

                return response
            #print(f"Actual response: after everything {response}")

            if format is None and downloaded_file:
                response = f"{lan['errorFileTooBig']} {downloaded_file}GB. {lan['errorFileTooBig1']}"
            else:
                response = lan["errorWerid"]
        

        else:
            #print(f"Lan:{lan}")
            #print("Going to do the processing of the text file!")
            valueddd  = ({language_name[laCode]})
            if lan is None:
                lan = en
            if valueddd is None:
                valueddd = "English"
            response = await chat.send_message(f"[SYSTEM NOTICE: SYSTEM LANGUAGE IS {valueddd} MAKE  SURE ALL INTERACTION ARE IN THE SELECTED LANGUAGE, if user says to respond in the specfic language then you can but not unless that]. The user message = {user_message_with_timestamp}")
            #print("The text file has been processed")
            response = await extract_response_text(response)
            save_chat_history(chat_history_path, chat)
            #print(f"Bot: {response}") #remove for  debugging

        return response

    except Exception as e:
        print(f"Error processing message: {str(e)}")
        error_message_to_send = f"{lan['errorException']}<@{(message.author.id)}>:\n```{str(e)}```"
        await message.channel.send(error_message_to_send)
        return e

async def handle_tagged_message(message: Message, lan) -> str:
    """
    Handles the logic when the bot is tagged in a message.
    """
    past_messages = []
    message_counts = {}  # Track duplicates
    #print("Inside")
    #print(lan)
    # Fetch last 20 messages, excluding the tagging message
    async for msg in message.channel.history(limit=21):
        if msg.id == message.id:
            continue

        msg_content = msg.content
        attachment_flag = ""

        # Check for attachments or links
        if msg.attachments or re.search(r'(https?://[^\s]+)', msg.content):
            if msg.content:
                attachment_flag = lan["ifmsgContent"]
            else:
                attachment_flag = lan["elsemsgContent"]

        msg_content += attachment_flag

        # Check for duplicates
        if msg_content in message_counts:
            message_counts[msg_content]["count"] += 1
            message_counts[msg_content]["users"].append(msg.author)
        else:
            message_counts[msg_content] = {
                "count": 1,
                "users": [msg.author],
                "timestamp": msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }

    # Build the formatted message list
    for msg_content, data in message_counts.items():
        if data["count"] > 1:
            user_mentions = ", ".join([f"{user.name}" for user in data["users"]])
            msg_content += f" ({lan['elsemsgContent']} {data['count']} {lan['buildMessageList1']} {user_mentions})"

        past_messages.append(
            f"{data['users'][0].name} {lan['appendMessageList']} <@{data['users'][0].id}> {lan['appendMessageList1']} {data['timestamp']} {lan['appendMessagelist2']} {msg_content}"
        )

    # Construct the final tagged message string
    tagging_user = message.author
    tagged_msg_content = message.content
    if message.attachments or re.search(r'(https?://[^\s]+)', message.content):
        tagged_msg_content += lan["requestMessageMediaCheck"]

    formatted_past_messages = "\n".join(past_messages)

    final_tagged_message = (
        f"{tagging_user.name} {lan['requestMessageMediaCheck']} {tagging_user.id} {lan['finalTaggedMessage1']} {tagged_msg_content} "
        f"{lan['finalTaggedMessage2']}"
        f"{lan['finalTaggedMessage3']}\n{formatted_past_messages}\n{lan['finalTaggedMessage4']}"
    )

    return final_tagged_message

@bot.event
async def on_message(message: Message) -> None:
    channel_id = message.channel.id
    if message.author == bot.user:  # Ignore messages from the bot itself
        return
    
    result = await api_Checker(api_keys, channel_id)
    if not result:
        lan = en
    if result:
        _, _, laCode = result
        lan = laCode
        lan = get_language_dict(lan)

    is_webhook_interaction = False
    webhook = None

    try:
        # Check if the message is a reply to a webhook
        if message.reference:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message.webhook_id in bot_webhook_ids:
                webhook = await bot.fetch_webhook(referenced_message.webhook_id)
                is_webhook_interaction = True

        if is_webhook_interaction and webhook:  # Handle webhook interactions
            if message.id in processing_messages:
                return # Already processing
            processing_messages[message.id] = True 

            asyncio.create_task(handle_message(message,lan,webhook=webhook)) # Use create_task

        # Check if the message mentions the bot or is a DM, ONLY if not a webhook interaction
        elif (bot.user in message.mentions or isinstance(message.channel, discord.DMChannel)) and not is_webhook_interaction:
            if message.id in processing_messages:
                return # Already processing
            processing_messages[message.id] = True

            asyncio.create_task(handle_message(message,lan))  # Use create_task
        
        # Process other bot commands (if any) - likely not needed if all handled by slash commands now
        await bot.process_commands(message) # KEEP THIS for any prefix-based commands that remain.

    except discord.NotFound:
        print(f"{lan['errorDiscordNotFound']} {message.id}")
    except discord.Forbidden:
        print(f"{lan['errorDiscordForbidden']} {message.id}")
    except Exception as e:
        print(f"{lan['errorException']} {message.id}: {str(e)}")
        error_message_to_send = f"{lan['errorException']} <@{(message.author.id)}>:\n```{str(e)}```"
        await message.channel.send(error_message_to_send)

async def handle_message(message,lan, webhook=None):
    #print("Handling message")
    channel_id = message.channel.id

    if channel_id in processing_messages:
        await message.channel.send(
            f"<@{(message.author.id)}> {lan['errorProcessingMessage']}"
        )
        return

    try:
        processing_messages[channel_id] = True
        await message.add_reaction('\U0001F534')

        response = await process_message(message, is_webhook=bool(webhook))  # webhook info passed

        if webhook:
            await send_message_webhook(webhook=webhook, response=response)
        else:
            await send_message_main_bot(message=message, response=response)

    except discord.NotFound:
        print(f"{lan['errorMessageNotFound']} {message.id}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = exc_tb.tb_frame.f_code.co_filename
        line_no = exc_tb.tb_lineno
        
        print(f"""Error Details:
        Type: {exc_type.__name__}
        Message: {str(e)}
        File: {fname}
        Line Number: {line_no}
        Full Traceback: 
        {traceback.format_exc()}""")
    finally:
        await message.remove_reaction('\U0001F534', bot.user)
        if channel_id in processing_messages:
            del processing_messages[channel_id]

@bot.event
async def on_guild_join(guild):
    lan = en
    """Sends a message when the bot joins a server."""
    try:
        system_channel = None
        # Check system channel permissions FIRST
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            system_channel = guild.system_channel

        # Fallback: Find *any* channel bot can send to if no system channel or no permissions
        if system_channel is None:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    system_channel = channel
                    break  # Stop searching once a suitable channel is found


        if system_channel:
            await system_channel.send(lan["firstMessage"])
        else:
            # No suitable channel found (rare)
            print(f"Could not find a channel to send a join message in guild {guild.name} (missing permissions).")


    except Exception as e:
        print(f"An error occurred in on_guild_join: {e}")

async def get_webhook_ids(bot):
  """
  Adds all webhook IDs created by the bot to the bot_webhook_ids set.
  """
  for guild in bot.guilds:
    for webhook in await guild.webhooks():
      if webhook.user == bot.user:
        bot_webhook_ids.add(webhook.id)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await get_webhook_ids(bot)
    print('Webhooks id done')
    #bot.loop.create_task(stats_logging_task())
    global api_keys
    api_keys = await load_api_keys()

    slash_handler = SlashCommandHandler(
        bot=bot,
        client=client, #changed from model to client
        model_name=model_name,
        config=config,
        system_instruction=system_instruction,
        webhooks=webhooks,
        bot_webhook_ids = bot_webhook_ids,
        api_keys = api_keys,
        GOOGLE_API_KEY = GOOGLE_API_KEY,
        get_channel_directory=get_channel_directory,
        get_bot_paths=get_bot_paths,
        load_chat_history=load_chat_history,
        save_chat_history=save_chat_history,
        check_expired_files=check_expired_files,
        load_webhook_system_instruction=load_webhook_system_instruction,
        send_message_webhook=send_message_webhook,
        get_language_dict=get_language_dict
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
            client = genai.Client(api_key=api_key)  # Test the key
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
                    "model_name": None, # Replace this or leave it if API key is managed elsewhere
                    "language": None
                }
            await save_api_json(api_keys)  # Save the updated api_keys dictionary
            
            loaded_keys = await load_api_keys() #Loss bandage  fix
            result = await api_Checker(loaded_keys, channel_id)  # Use your api_Checker
            if result:
                _, _, lan = result
                lan = get_language_dict(lan)
            else:
                lan = en
            await interaction.followup.send(lan["comset_api_key-followup"], ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"{e}", ephemeral=True)

    await slash_handler.setup_slash_commands()
    await bot.tree.sync()

# STEP 5: MAIN ENTRY POINT
def main():
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
