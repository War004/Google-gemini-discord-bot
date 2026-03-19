import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from discord.ext import commands
import discord

from cogs.langauges.LanguageProvider import LanguageProvider
from cogs.startUp.StartUp import StartUp
from cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from cogs.chat.MediaProcessor import MediaProcessor
from cogs.chat.MessageProcessor import MessageProcessor
from utils.reader import fileReader
from Mana import Mana

from google.genai.types import SafetySetting, Tool, UrlContext, GoogleSearch, ToolCodeExecution, GenerateContentConfig

from AppContainer import AppContainer
from BloomFilter import BloomFilter
from translator.Translator import Translator
from cogs.commands.WebhookCom import WebhookCom
from cogs.commands.ConfigCom import ConfigCom

load_dotenv()

#load the app container
appContainer = AppContainer()
appContainer.init()

# --- File paths ---
system_instruction_path = Path("data") / "system_instruction.txt"
language_path = Path("locales")
chat_history_base = Path("data") / "chat"

# --- Repositories ---
language_provider = LanguageProvider(language_path)
language_map = language_provider.language_map

server_default_lan = {}

#create the bloom filter
api_bloom_file = BloomFilter(expected_items=1000000,false_positive_rate=0.01)

lan_bloom_filter = BloomFilter(expected_items=1000000,false_positive_rate=0.01)\

#todo update the values of bloom filter for lan and api based on db
#load the translator class that gives the language code
translator = Translator(
    channel_config_repo=appContainer.channel_config_repo,
    lan_channel_entry_bloom_filter=lan_bloom_filter,
    server_default_lan = server_default_lan,
    language_map=language_map
)

# --- System instruction ---
system_instruction = fileReader(system_instruction_path)
if system_instruction is None:
    print("No system instruction provided. Please provide a system instruction in the system_instruction.txt file.")
    exit()


# --- StartUp (resolves app ID, builds default GenAI config) ---
start_up = StartUp(os.getenv("DISCORD_TOKEN"), system_instruction)

#--default config--

default_safety = [
    SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold="OFF"),
    SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold="OFF"),
    SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold="OFF"),
    SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold="OFF")
]

default_tools = [
    Tool(url_context=UrlContext()),
    Tool(code_execution=ToolCodeExecution),
    Tool(googleSearch=GoogleSearch()),
]
default_config = GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=1.0,
    top_p=0.95,
    top_k=20,
    candidate_count=1,
    max_output_tokens=65536,
    safety_settings=default_safety,
    tools=default_tools
)
# --- Chat handling ---

chat_history_handler = ChatHistoryHandler(str(chat_history_base))
media_processor = MediaProcessor()
message_processor = MessageProcessor(
    default_config=default_config,
    channel_config_repo=appContainer.channel_config_repo,
    media_hadnler_repo=appContainer.media_handler_repo,
    persona_repo=appContainer.persona_repo,
    webhook_repo=appContainer.webhook_info_repo,
    media_processor=media_processor,
    chat_history_handler=ChatHistoryHandler(base_path=chat_history_base),
    lock=appContainer.lock
)

# --- Intents (need message_content for reading message text) ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# --- Create and run the bot ---
bot = Mana(
    command_prefix=commands.when_mentioned,
    intents=intents,
    message_processor=message_processor,
    webhook_repo=appContainer.webhook_info_repo,
    language_map=language_map,
    server_default_lan = server_default_lan
)

webhook_slash_command = WebhookCom(
    bot = bot,
    lan_map=language_map,
    api_bloom=api_bloom_file,
    translator=translator,
    webhook_repo=appContainer.webhook_info_repo,
    persona_repo=appContainer.persona_repo,
    chat_history_handler=chat_history_handler
)

config_slash_command = ConfigCom(
    bot = bot,
    lan_map=language_map,
    api_bloom=api_bloom_file,
    translator=translator,
    channel_config_repo=appContainer.channel_config_repo
)

bot.webhook_slash_command = webhook_slash_command
bot.config_slash_command = config_slash_command

bot.run(os.getenv("DISCORD_TOKEN"))