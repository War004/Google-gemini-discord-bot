import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from discord.ext import commands
import discord

from src.cogs.langauges.string_translator import StringTranslator
from src.cogs.startUp.StartUp import StartUp
from src.cogs.chat.MediaProcessor import MediaProcessor
from src.cogs.chat.MessageProcessor import MessageProcessor
from src.utils.reader import fileReader
from src.Mana import Mana

from google.genai.types import SafetySetting, Tool, UrlContext, GoogleSearch, ToolCodeExecution, GenerateContentConfig

from src.AppContainer import AppContainer
from src.BloomFilter import BloomFilter
from src.cogs.commands.WebhookCom import WebhookCom
from src.cogs.commands.ConfigCom import ConfigCom
from src.cogs.commands.CommonCom import CommonCom

load_dotenv()

#create the bloom filter
api_bloom_filter = BloomFilter(expected_items=100000,false_positive_rate=0.01)

lan_bloom_filter = BloomFilter(expected_items=100000,false_positive_rate=0.01)

# --- File paths ---
system_instruction_path = Path("data") / "system_instruction.txt"
language_path = Path("locales")
chat_history_base = Path("data") / "chat"

#load the app container
appContainer = AppContainer(
    api_bloom_filter,
    lan_bloom_filter,
    chat_history_base
)
appContainer.init()


string_translator = StringTranslator(
    language_path,
    appContainer.channel_config_repo,
    lan_bloom_filter
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

#Tool(code_execution=ToolCodeExecution),
default_tools = [
    Tool(url_context=UrlContext()),
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

media_processor = MediaProcessor()
message_processor = MessageProcessor(
    default_config=default_config,
    channel_config_repo=appContainer.channel_config_repo,
    media_hadnler_repo=appContainer.media_handler_repo,
    persona_repo=appContainer.persona_repo,
    webhook_repo=appContainer.webhook_info_repo,
    media_processor=media_processor,
    chat_history_handler=appContainer.chat_history_handler,
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
    string_translation_service=string_translator,
    message_processor=message_processor,
    webhook_repo=appContainer.webhook_info_repo,
    channel_config_repo=appContainer.channel_config_repo,
    api_bloom=api_bloom_filter,
    lan_bloom=lan_bloom_filter
)

webhook_slash_command = WebhookCom(
    bot = bot,
    api_bloom=api_bloom_filter,
    channel_config=appContainer.channel_config_repo,
    webhook_repo=appContainer.webhook_info_repo,
    person_cache=appContainer.person_cache,
    chat_history_handler=appContainer.chat_history_handler,
    string_translator=string_translator,
    media_repo=appContainer.media_handler_repo
)

config_slash_command = ConfigCom(
    bot = bot,
    string_translator=string_translator,
    channel_config_repo=appContainer.channel_config_repo
)

common_slash_command = CommonCom(
    bot=bot,
    main_bot_sys=system_instruction,
    string_translator=string_translator,
    chat_history_manager=appContainer.chat_history_handler,
    media_handler_repo=appContainer.media_handler_repo,
    channel_config_repo=appContainer.channel_config_repo,
    webhook_repo=appContainer.webhook_info_repo
)

bot.webhook_slash_command = webhook_slash_command
bot.config_slash_command = config_slash_command
bot.common_slash_command = common_slash_command

bot.run(os.getenv("DISCORD_TOKEN"))