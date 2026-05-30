import discord

from discord.ext import commands
from charset_normalizer import from_bytes
from discord import app_commands
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.PersonaRepo import PersonaRepo
from src.BloomFilter import BloomFilter
from src.loader.Results import Error,Success
from src.utils.PngParserResults import PngParserResults

from database.domain.WebhookInfo import WebhookInfo
from typing import Optional
from PIL import Image
import io
import base64
import json
import re

import logging
import discord
import time
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.types import SafetySetting, Tool, ThinkingConfig, Content, Part
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.domain.ChannelConfig import ChannelConfig
from src.cogs.langauges.string_translator import StringTranslator
from src.config import LAN_LIST, MODEL_LIST
import mimetypes
import magic
import sys
import traceback
import os
import json
import pickle
import re

class ConfigCom(commands.Cog):
    def __init__(
            self,
            bot: commands.Bot,
            string_translator: StringTranslator,
            channel_config_repo: ChannelConfigRepo
            ):
        self.bot = bot
        self.string_translator = string_translator
        self.channel_repo = channel_config_repo
    
    async def create_dropdown(self, options_list: list[dict[str,str]], interaction: discord.Interaction, placeholder: str, callback):

        if(len(options_list)> 25):
            msg = await self.string_translator.translate_text(
                channel_id=str(interaction.channel_id),
                string_key=None,
                lan_code=None,
                payload=[],
                direct_message="List contains more than 25 items. Showing only the first 25 options."
            )
            await interaction.followup.send(msg)

        try:
            # 1. Slice the list directly to get the first 25 items
            safe_items = options_list[:25]

            # 2. Extract the 'label' and 'value' from each dictionary in the list
            options = [
                discord.SelectOption(label=key, value=value) 
                for item in safe_items 
                for key, value in item.items()
            ]

            # 3. Use capital V for View()
            view = discord.ui.View()
            dropdown = discord.ui.Select(
                placeholder=placeholder,
                options=options
            )
            dropdown.callback = callback
            view.add_item(dropdown)

            return view
        except Exception as e:
            match type(e):
                case discord.Forbidden:
                    msg = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message=f"No permission to manage webhooks in {interaction.channel.name}."
                    )
                    await interaction.followup.send(msg)
                case discord.HTTPException:
                    msg = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message="An HTTP error occurred while fetching webhooks."
                    )
                    await interaction.followup.send(msg)
                case _:
                    msg = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message="An unexpected error occurred while generating the webhook list."
                    )
                    await interaction.followup.send(msg)
            print(f"[WebhookCom] create_webhook_dropdown Exception: {type(e).__name__}: {e}")
            return None
        
    config_group = app_commands.Group(name="config", description="Config the configurable options")

    @config_group.command(
        name=app_commands.locale_str("model"),
        description=app_commands.locale_str("Modify the model used for a channel")
    )
    @app_commands.choices(selected_model=MODEL_LIST)
    async def modify_model_used(self, interaction: discord.Interaction, selected_model: str):
        # selected_model now automatically contains the 'value' (e.g., 'gemini-pro')
        # The user's selection is passed directly into the function!
        
        await interaction.response.defer()

        # Save the new entry using the parameter
        results = await self.channel_repo.update_model_name(
            channel_id=str(interaction.channel_id),
            model_name=selected_model
        )

        # Handle the results immediately
        match results:
            case Error():
                print("Error while modify the db entry for a channel")
                print(f"\n{results.message}\n{results.exception}\n")
                msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Some error happened.\n``` {results.message} \n```"
                )
                await interaction.followup.send(msg)
                
            case Success():
                msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Changed model to: {selected_model} for {interaction.channel_id}"
                )
                await interaction.followup.send(msg)
    
    @config_group.command(
        name=app_commands.locale_str("language"),
        description=app_commands.locale_str("Configure the language used on per Channel bases.")
    )
    @app_commands.choices(selected_language=LAN_LIST)
    async def modify_channel_langauge(self, interaction: discord.Interaction, selected_language: str):
        await interaction.response.defer()

        #save the entry in the db
        results = await self.channel_repo.update_lan_code(
            channel_id=str(interaction.channel_id),
            lan_code=selected_language
        )

        match results:
            case Error():
                print("Failed to save the default lan code in the db\n")
                print(f"Error message: {results.message}")
                msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Can't save the lan entry to the db: \n```Reason: {results.message}\nCode:{results.code}\nSolution:{results.solution}```"
                )
                await interaction.followup.send(msg)
            case Success():
                msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Changed the language to {selected_language} for {interaction.channel_id}"
                )
                await interaction.followup.send(msg)

    @config_group.command(
        name=app_commands.locale_str("api-key"),
        description=app_commands.locale_str("Add an api key")
    )
    @app_commands.describe(
        api_key=app_commands.locale_str("[Don't share the api key with anyone] Google gemini api key")
    )
    async def set_api_key(self, interaction: discord.Interaction,api_key: str):
        await interaction.response.defer()

        #save the entry in the db
        result = await self.channel_repo.update_api_key(
            channel_id=str(interaction.channel_id),
            api_key=api_key
        )

        match result:
            case Error():
                print("Falied to save the api key in the db.\n")
                print(f"Error: {result.message}\n")
                print(f"{result.exception}\n")
                msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Falied to save api in the db.\n```Error Message:{result.message}\nError Code:{result.code}\nSolution:{result.solution}\n```"
                )
                await interaction.followup.send(msg)
            
            case Success():
                msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Api set for channel <#{interaction.channel_id}> by <@{interaction.user.id}>"
                )
                await interaction.followup.send(msg)