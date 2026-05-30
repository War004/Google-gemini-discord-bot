import discord

from discord.ext import commands
from charset_normalizer import from_bytes
from discord import app_commands
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.PersonaRepo import PersonaRepo
from src.cogs.langauges.string_translator import StringTranslator
from src.BloomFilter import BloomFilter

from src.loader.Results import Success, Error
from src.utils.PngParserResults import PngParserResults

from discord.webhook import Webhook

from database.domain.WebhookInfo import WebhookInfo
from typing import Optional
from PIL import Image
import io
import base64
import json
import re
import asyncio

import logging
import discord
import time
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.types import SafetySetting, Tool, ThinkingConfig, Content, Part
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from database.repo.MediaHandlerRepo import MediaHandlerRepo
import mimetypes
import magic
import sys
import traceback
import os
import json
import pickle
import re

class CommonCom(commands.Cog):
    def __init__(
            self,
            bot: commands.Bot,
            main_bot_sys: str,
            string_translator: StringTranslator,
            chat_history_manager: ChatHistoryHandler,
            media_handler_repo: MediaHandlerRepo,
            channel_config_repo: ChannelConfigRepo,
            webhook_repo: WebhookInfoRepo
    ):
        self.bot = bot
        self.bot_system_ins_token = 9992
        self.main_bot_sys = main_bot_sys
        self.string_translator = string_translator
        self.self_history_manager = chat_history_manager
        self.media_handler_repo = media_handler_repo
        self.channel_repo = channel_config_repo
        self.webhook_repo = webhook_repo
    
    """
    3 commands in total,
    check token,
    ping defer,
    info
    """
    
    async def create_webhook_dropdown(self, interaction: discord.Interaction, placeholder: str, callback):

        if isinstance(interaction.channel, discord.DMChannel):
            return

        try:
            #get all webhook
            webhooks = await interaction.channel.webhooks()
            bot_webhook = []

            for webhook in webhooks:
                if(webhook.user == self.bot.user):
                    bot_webhook.append(webhook)

            options = [
                discord.SelectOption(label=self.bot.user.name,value="main_bot_")
            ]
            #add the options,
            #10 webhooks are the limit far more then 25 item in discord list
            if webhooks is not None and len(webhooks) > 0:
                options += [
                    *[discord.SelectOption(label=webhook.name,value=str(webhook.id)) for webhook in bot_webhook]
                ]

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
                    message = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message=f"No permission to manage webhooks in {interaction.channel.name}."
                    )
                    await interaction.followup.send(message)
                case discord.HTTPException:
                    message = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message="An HTTP error occurred while fetching webhooks."
                    )
                    await interaction.followup.send(message)
                case _:
                    message = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message="An unexpected error occurred while generating the webhook list."
                    )
                    await interaction.followup.send(message)
            print(f"[WebhookCom] create_webhook_dropdown Exception: {type(e).__name__}: {e}")
            return None
        
    @app_commands.command(
        name=app_commands.locale_str("check-token-usage"),
        description=app_commands.locale_str("Check the total token used by the bot.")
    )
    async def check_token(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()

        if isinstance(interaction.channel, discord.DMChannel):
            #get the channel details
            results = await self.channel_repo.get(str(interaction.channel_id))

            match results:
                case Error():
                    message = await self.string_translator.translate_text(
                        channel_id=str(interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message="Something happened while fetching channel config from db"
                    )
                    await interaction.followup.send(message)
                    return
            
            data = results.data

            if data is None:
                message = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message="Channel not configured"
                )
                await interaction.followup.send(message)
                return
            
            if data.api_key is None:
                message = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message="APi key is empty."
                )
                await interaction.followup.send(message)
                return
            
            #load the chat history with system 

            chat_history = await self.self_history_manager.load(
                channel_id=str(interaction.channel_id),
                chat_id=f"main_bot_{interaction.channel_id}"
            )

            cus_client = genai.Client(api_key=data.api_key)

            try:
                result = await cus_client.aio.models.count_tokens(
                    model="gemini-flash-latest",
                    contents=chat_history
                )

                sys_token = self.bot_system_ins_token[0] if isinstance(self.bot_system_ins_token, tuple) else self.bot_system_ins_token
                total_token = result.total_tokens + sys_token

                message = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message=f"Total token used: {total_token}"
                )
                await interaction.followup.send(message)

            except Exception as e:
                message = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message="An error occurred while counting tokens."
                )
                await interaction.followup.send(message)
                print(f"[check_token] Exception: {e}")
                return
        else:
            async def select_callback(select_interaction: discord.Interaction):
                await select_interaction.response.defer()
                selected_value = select_interaction.data["values"][0]
                
                results = await self.channel_repo.get(str(select_interaction.channel_id))
                match results:
                    case Error():
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message="Something happened while fetching channel config from db"
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                    case _:
                        data = results.data
                
                if data is None or data.api_key is None:
                    message = await self.string_translator.translate_text(
                        channel_id=str(select_interaction.channel_id),
                        string_key=None,
                        lan_code=None,
                        payload=[],
                        direct_message="Channel not configured or API key is empty."
                    )
                    await select_interaction.followup.send(message, ephemeral=True)
                    return
                
                cus_client = genai.Client(api_key=data.api_key)
                
                if selected_value == "main_bot_":
                    chat_history = await self.self_history_manager.load(
                        channel_id=str(select_interaction.channel_id),
                        chat_id=f"main_bot_{select_interaction.channel_id}"
                    )
                    
                    try:
                        result = await cus_client.aio.models.count_tokens(
                            model="gemini-flash-latest",
                            contents=chat_history
                        )
                        sys_token = self.bot_system_ins_token[0] if isinstance(self.bot_system_ins_token, tuple) else self.bot_system_ins_token
                        total_token = result.total_tokens + sys_token
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message=f"Total token used: {total_token}"
                        )
                        await select_interaction.followup.send(message)
                    except Exception as e:
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message="An error occurred while counting tokens."
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        print(f"[check_token] main_bot_ Exception: {e}")
                else:
                    webhook_id = int(selected_value)
                    webhook_res = await self.webhook_repo.get(webhook_id)
                    
                    match webhook_res:
                        case Error():
                            message = await self.string_translator.translate_text(
                                channel_id=str(select_interaction.channel_id),
                                string_key=None,
                                lan_code=None,
                                payload=[],
                                direct_message="Something happened while fetching webhook config from db"
                            )
                            await select_interaction.followup.send(message, ephemeral=True)
                            return
                    
                    info = webhook_res.data

                    
                    if info is None:
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message="Webhook is not configured."
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                        
                    chat_history = await self.self_history_manager.load(
                        channel_id=str(select_interaction.channel_id),
                        chat_id = f"{webhook_id}_{select_interaction.channel_id}"
                    )
                    
                    system_info = info.webhook_system_information
                    
                    if len(chat_history) == 0:
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message="No history for this webhook."
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                    if len(system_info) == 0:
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message="No system info found"
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                    try:
                        count_hist_task = cus_client.aio.models.count_tokens(
                            model="gemini-flash-latest",
                            contents=chat_history
                        )
                        
                        if system_info:
                            count_sys_task = cus_client.aio.models.count_tokens(
                                model="gemini-flash-latest",
                                contents=system_info
                            )
                            hist_res, sys_res = await asyncio.gather(count_hist_task, count_sys_task)
                            total_token = hist_res.total_tokens + sys_res.total_tokens
                        else:
                            hist_res = await count_hist_task
                            total_token = hist_res.total_tokens
                            
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message=f"Total token used: {total_token}"
                        )
                        await select_interaction.followup.send(message)
                    except Exception as e:
                        message = await self.string_translator.translate_text(
                            channel_id=str(select_interaction.channel_id),
                            string_key=None,
                            lan_code=None,
                            payload=[],
                            direct_message="An error occurred while counting tokens."
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        print(f"[check_token] webhook Exception: {e}")

            placeholder_msg = await self.string_translator.translate_text(
                channel_id=str(interaction.channel_id),
                string_key=None,
                lan_code=None,
                payload=[],
                direct_message="Select a bot to check token usage"
            )
            view = await self.create_webhook_dropdown(interaction, placeholder_msg, select_callback)
            if view:
                select_msg = await self.string_translator.translate_text(
                    channel_id=str(interaction.channel_id),
                    string_key=None,
                    lan_code=None,
                    payload=[],
                    direct_message="Select a bot to check token usage:"
                )
                await interaction.followup.send(select_msg, view=view) 
    
    @app_commands.command(
        name=app_commands.locale_str("info"),
        description=app_commands.locale_str("Get some basic info about the bot.")
    )
    async def get_info(self,interaction: discord.Interaction):

        await interaction.response.defer()

        channel_id = str(interaction.channel_id)
        channel_config = await self.channel_repo.get(channel_id)

        match channel_config:
            case Error():
                await interaction.followup.send(channel_config.message)
                return
        channel_data = channel_config.data

        string = f"\n```Api Key: {"Exists" if(channel_data.api_key) else "None"}\nDefault model: {channel_data.model_name}\nDefault language: {channel_data.default_lan_code}```\n"

        message = await self.string_translator.translate_text(
            channel_id=channel_id,
            string_key=None,
            lan_code=None,
            payload=[],
            direct_message=string
        )
        await interaction.followup.send(message)
    @app_commands.command(
        name=app_commands.locale_str("ping"),
        description=app_commands.locale_str("Check the bot's latency.")
    )
    async def ping_defer(self, interaction: discord.Interaction):

        await interaction.response.defer()

        latency = round(self.bot.latency * 1000)
        message = await self.string_translator.translate_text(
            channel_id=str(interaction.channel_id),
            string_key=None,
            lan_code=None,
            payload=[],
            direct_message=f"Pong! Bot latency is {latency}ms."
        )
        await interaction.followup.send(message)
    
    @app_commands.command(
        name=app_commands.locale_str("reset-history"),
        description=app_commands.locale_str("Resets the chat history for a specfic bot or a webhook")
    )
    async def reset_chat(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer()

        if isinstance(interaction.channel, discord.DMChannel):
            chat_id = f"main_bot_{interaction.channel_id}"

            final_message, solution = await self._reset_chat_history(
                str(interaction.channel_id), chat_id
                )
            
            await interaction.followup.send(final_message)
        #we need to check if the directory for this channel exists or not.
        #no need to strticly check the channel is tied to a api key

        async def select_callback(select_interaction: discord.Interaction):
            await select_interaction.response.defer()
            selected_value = select_interaction.data["values"][0]

            print(f"{selected_value}\n")

            #extected values are webhook id and the string value "main_bot_" for the main bot instance
            match selected_value:
                case "main_bot_":
                    chat_id = f"main_bot_{select_interaction.channel_id}"
                case _:
                    chat_id = f"{selected_value}_{select_interaction.channel_id}"
            
            if selected_value == "main_bot_":
                # Main bot: reset with empty history
                final_message, solution = await self._reset_chat_history(
                    str(select_interaction.channel_id), chat_id
                )
                await select_interaction.followup.send(final_message)
            else:
                #We can now load the chat history if it is empty
                #Then it must have been a main bot instance
                #If it is a webhook, then something might be wrong with the webhook
                #as webhook have prebacked system instruction in them.

                chat_history = await self.self_history_manager.load(
                    channel_id=str(select_interaction.channel_id),
                    chat_id = chat_id
                )

                match len(chat_history):
                    case 0:
                        translated_message, translated_soltuion = await asyncio.gather(
                            self.string_translator.translate_text(
                                channel_id=str(select_interaction.channel_id),
                                string_key=None,
                                lan_code=None,
                                payload=[],
                                direct_message="The selected webhook returned a empty list. Webhook are not supposed to return chat history with 0 lenght."
                            ),
                            self.string_translator.translate_text(
                                channel_id=str(select_interaction.channel_id),
                                string_key=None,
                                lan_code=None,
                                payload=[],
                                direct_message="It is preferred that you remove the webhook."
                            )
                        )
                        await select_interaction.followup.send(
                            f"```text\nMessage:{translated_message}\nSolution:{translated_soltuion}\n```"
                        )
                        return

                    case _:
                        if(len(chat_history[0].parts)==2):
                            print("Webhook with persona image")
                            chat_history = chat_history[:9]
                        else:
                            chat_history = chat_history[:5]
                        #todo overwrite chat history 
                        #hardcoded value, needs to changed if persona command is changed in the future
                
                final_message, solution = await self._reset_chat_history(
                    str(select_interaction.channel_id), chat_id, chat_history
                    )
                
                await select_interaction.followup.send(final_message)
        
        placeholder_msg = await self.string_translator.translate_text(
            channel_id=str(interaction.channel_id),
            string_key=None,
            lan_code=None,
            payload=[],
            direct_message="Reset chat history menu"
        )
        select_msg = await self.string_translator.translate_text(
            channel_id=str(interaction.channel_id),
            string_key=None,
            lan_code=None,
            payload=[],
            direct_message="Select the webhook"
        )
        view = await self.create_webhook_dropdown(interaction, placeholder_msg, select_callback)
        if view:
            await interaction.followup.send(select_msg, view=view)
        
    async def _reset_chat_history(
    self,
    channel_id: str,
    chat_id: str,
    chat_history: list = None
) -> tuple[str, str]:
        """Returns (translated_message, solution)."""
        if chat_history is None:
            chat_history = []
        result_history, result_media = await asyncio.gather(
            self.self_history_manager.save(
                channel_id=channel_id,
                chat_id=chat_id,
                chat_history=chat_history
            ),
            self.media_handler_repo.delete(chat_id=chat_id)
        )

        match (result_history, result_media):
            case (False, Error() as err):
                msg = (
                    "Multiple errors occurred\n```text\n"
                    "Unable to remove the chat file from the disk.\n"
                    f"{(err.message or 'Unable to remove media')[:2000]}\n```"
                )
                solution = "Remove the webhook."
            case (False, Success()):
                msg = (
                    "History removal failed.\n```text\n"
                    "Unable to remove the chat file from the disk.\n"
                    "Media history removed."
                )
                solution = "Remove the webhook."
            case (True, Error() as err):
                msg = (
                    "Media history removal failed.\n```text\n"
                    "Removed chat file from the disk.\n"
                    f"{(err.message or 'Unable to remove media')[:2000]}"
                )
                solution = err.solution or "Remove the webhook."
            case (True, Success()):
                msg = "Chat history reset done for the selected character."
                solution = ""

        translated_msg = await self.string_translator.translate_text(
            channel_id=channel_id,
            string_key=None,
            lan_code=None,
            payload=[],
            direct_message=msg
        )
        return translated_msg, solution