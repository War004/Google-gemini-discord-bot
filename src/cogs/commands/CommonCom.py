import discord

from discord.ext import commands
from charset_normalizer import from_bytes
from discord import app_commands
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.PersonaRepo import PersonaRepo
from src.translator.translator import Translator
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
from src.translator.lan_key import LangKey
from src.BloomFilter import BloomFilter
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
            string_translator: Translator,
            api_bloom: BloomFilter,
            lan_bloom: BloomFilter,
            chat_history_manager: ChatHistoryHandler,
            media_handler_repo: MediaHandlerRepo,
            channel_config_repo: ChannelConfigRepo,
            webhook_repo: WebhookInfoRepo
    ):
        self.bot = bot
        self.bot_system_ins_token = 9992
        self.main_bot_sys = main_bot_sys
        self.string_translator = string_translator
        self.api_bloom = api_bloom
        self.lan_bloom = lan_bloom
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
    
    async def create_webhook_dropdown(self, interaction: discord.Interaction, placeholder: str, lan_code: str, callback):

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
            # [AutoFix] Replaced match type(e) with isinstance — match type(e) used structural
            # pattern matching, causing the first case to always match as a capture pattern.
            if isinstance(e, discord.Forbidden):
                payload = {
                    "channel_id":interaction.channel_id
                }
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_NO_MANAGE_PERM,
                    lan_code=lan_code,
                    payload=payload
                )
                await interaction.followup.send(message)
            elif isinstance(e, discord.HTTPException):
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.FETCH_WEBHOOK_HTTP_ERROR,
                    lan_code=lan_code,
                )
                await interaction.followup.send(message)
            else:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_LIST_UNKNOWN_ERROR,
                    lan_code=lan_code,
                )
                await interaction.followup.send(message)
            print(f"[CommonCom] create_webhook_dropdown Exception: {type(e).__name__}: {e}")
            return None
    

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        #This was added as hosting happens in India, latency is high between US and India
        await interaction.response.defer()
        requires_api = {"check-token-usage"}

        api_hit = self.api_bloom.check(interaction.channel_id)
        lan_hit = self.lan_bloom.check(interaction.channel_id)
        local_lan_code = str(interaction.locale).split("-")[0]

        if lan_hit:
            db_result = await self.channel_repo.get_lan_code(interaction.channel_id)
            match db_result:
                case Success():
                    if(db_result.data):
                        local_lan_code = db_result.data
                case Error():
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.LAN_DATA_NOT_SUCCESSFUL,
                        lan_code=local_lan_code,
                    )
                    await interaction.followup.send(message)

        if interaction.command.name in requires_api:
            if api_hit == False:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.API_REQUIRED,
                    lan_code=local_lan_code,
                )
                await interaction.followup.send(message)
                return False
        interaction.extras[LangKey.LAN_CODE] = local_lan_code
        return True

    @app_commands.command(
        name=app_commands.locale_str(LangKey.NAME_CHECK_TOKEN),
        description=app_commands.locale_str(LangKey.DESC_CHECK_TOKEN)
    )
    async def check_token(
        self,
        interaction: discord.Interaction,
    ):
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        if isinstance(interaction.channel, discord.DMChannel):
            #get the channel details
            results = await self.channel_repo.get(str(interaction.channel_id))

            match results:
                case Error():
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.CHANNEL_CONFIG_UNKNOWN_ERROR,
                        lan_code=lan_code,
                    )
                    await interaction.followup.send(message)
                    return
            
            data = results.data

            if data is None:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CHANNEL_CONFIG_NOT_SET,
                    lan_code=lan_code,
                )
                await interaction.followup.send(message)
                return
            
            if data.api_key is None:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.NO_API,
                    lan_code=lan_code
                )
                await interaction.followup.send(message)
                return
            
            #load the chat history with system 

            chat_history = await self.self_history_manager.load(
                channel_id=str(interaction.channel_id),
                chat_id=f"main_bot_{interaction.channel_id}"
            )

            cus_client = genai.Client(vertexai=False,api_key=data.api_key)

            try:
                result = await cus_client.aio.models.count_tokens(
                    model="gemini-flash-latest",
                    contents=chat_history
                )

                sys_token = self.bot_system_ins_token[0] if isinstance(self.bot_system_ins_token, tuple) else self.bot_system_ins_token
                total_token = result.total_tokens + sys_token

                payload = {
                    "total_token": total_token
                }
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.TOTAL_TOKEN_USED,
                    lan_code=lan_code,
                    payload=payload
                )
                await interaction.followup.send(message)

            except Exception as e:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.COUNT_TOKEN_ERROR,
                    lan_code=lan_code,
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
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.CHANNEL_CONFIG_UNKNOWN_ERROR,
                            lan_code=lan_code,
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                    case _:
                        data = results.data
                
                if data is None:
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.CHANNEL_CONFIG_NOT_SET,
                        lan_code=lan_code,
                    )
                    await select_interaction.followup.send(message, ephemeral=True)
                    return
                
                cus_client = genai.Client(vertexai=False,api_key=data.api_key)
                
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
                        payload = {
                            "total_token":total_token
                        }
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.TOTAL_TOKEN_USED,
                            lan_code=lan_code,
                            payload=payload
                        )
                        await select_interaction.followup.send(message)
                    except Exception as e:
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.COUNT_TOKEN_ERROR,
                            lan_code=lan_code,
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        print(f"[check_token] main_bot_ Exception: {e}")
                else:
                    webhook_id = int(selected_value)
                    webhook_res = await self.webhook_repo.get(webhook_id)
                    
                    match webhook_res:
                        case Error():
                            message = self.string_translator.get_translation_via_bypass_db(
                                string_key=LangKey.CHANNEL_CONFIG_UNKNOWN_ERROR,
                                lan_code=lan_code,
                            )
                            await select_interaction.followup.send(message, ephemeral=True)
                            return
                    
                    info = webhook_res.data

                    
                    if info is None:
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.WEBHOOK_NOT_CONFIGURED,
                            lan_code=lan_code,
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                        
                    chat_history = await self.self_history_manager.load(
                        channel_id=str(select_interaction.channel_id),
                        chat_id = f"{webhook_id}_{select_interaction.channel_id}"
                    )
                    
                    system_info = info.webhook_system_information
                    
                    if len(chat_history) == 0:
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.WEBHOOK_NO,
                            lan_code=lan_code
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        return
                    if len(system_info) == 0:
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.WEBHOOK_NO_SYSTEM_INFO,
                            lan_code=lan_code,
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

                            payload = {
                                "total_token":total_token
                            }
                        else:
                            hist_res = await count_hist_task
                            total_token = hist_res.total_tokens
                            payload = {
                                "total_token":total_token
                            }
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.TOTAL_TOKEN_USED,
                            lan_code=lan_code,
                            payload=payload
                            )
                        await select_interaction.followup.send(message)
                    except Exception as e:
                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.COUNT_TOKEN_ERROR,
                            lan_code=lan_code
                        )
                        await select_interaction.followup.send(message, ephemeral=True)
                        print(f"[check_token] webhook Exception: {e}")

            placeholder_msg = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.CHECK_TOKEN_SELECT_BOT,
                lan_code=lan_code
            )
            view = await self.create_webhook_dropdown(interaction, placeholder_msg,lan_code, select_callback)
            if view:
                select_msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CHECK_TOKEN_SELECT_BOT,
                    lan_code=lan_code
                )
                await interaction.followup.send(select_msg, view=view) 
    
    @app_commands.command(
        name=app_commands.locale_str(LangKey.NAME_INFO),
        description=app_commands.locale_str(LangKey.NAME_INFO)
    )
    async def get_info(self,interaction: discord.Interaction):
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        channel_id = str(interaction.channel_id)
        channel_config = await self.channel_repo.get(channel_id)

        match channel_config:
            case Error():
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CHANNEL_CONFIG_UNKNOWN_ERROR,
                    lan_code=lan_code
                )
                
                await interaction.followup.send(message)
                return
            
        channel_data = channel_config.data

        payload = {
            "api_state": "Exists" if(channel_data.api_key) else "None",
            "model_name": channel_data.model_name,
            "lan_code": channel_data.default_lan_code
        }

        message = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.INFO_STRING_VALUE,
            lan_code=lan_code,
            payload=payload
        )
        await interaction.followup.send(message)

    @app_commands.command(
        name=app_commands.locale_str(LangKey.NAME_PING),
        description=app_commands.locale_str(LangKey.DESC_PING)
    )
    async def ping_defer(self, interaction: discord.Interaction):

        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        latency = round(self.bot.latency * 1000)
        message = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.LATENCY,
            lan_code=lan_code,
            payload = {"latency": latency}
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
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        if isinstance(interaction.channel, discord.DMChannel):
            chat_id = f"main_bot_{interaction.channel_id}"

            final_message, solution = await self._reset_chat_history(
                lan_code,
                str(interaction.channel_id),
                chat_id
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
                    lan_code, str(select_interaction.channel_id), chat_id
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
                        translated_message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.WEBHOOK_NO_HISTORY,
                            lan_code=lan_code
                        )

                        await select_interaction.followup.send(translated_message)
                        return

                    case _:
                        if(len(chat_history[0].parts)==2):
                            print("Webhook with persona image")
                            chat_history = chat_history[:9]
                        else:
                            # [AutoFix] Changed from [:5] to [:6] — creation now produces
                            # 4 inline prompts + 2 curated entries (roleplay start + first_message)
                            chat_history = chat_history[:6]
                        #todo overwrite chat history 
                        #hardcoded value, needs to changed if persona command is changed in the future
                
                final_message, solution = await self._reset_chat_history(
                    lan_code, str(select_interaction.channel_id), chat_id, chat_history
                    )
                
                await select_interaction.followup.send(final_message)
        
        placeholder_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.RESET_HISTORY_MENU,
            lan_code=lan_code
        )
        select_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.WEBHOOK_SELECT,
            lan_code=lan_code,
        )
        view = await self.create_webhook_dropdown(interaction, placeholder_msg, lan_code, select_callback)
        if view:
            await interaction.followup.send(select_msg, view=view)
        
    async def _reset_chat_history(
    self,
    lan_code: str,
    channel_id: str,
    chat_id: str,
    chat_history: list = None
) -> tuple[str, str]:
        """Returns (translated_message, solution)."""
        if chat_history is None:
            chat_history = []
        # NOTE: lan_code is not passed to DB repository methods because cogs use Success/Error wrapper checks for user-facing translations.
        result_history, result_media = await asyncio.gather(
            self.self_history_manager.save(
                channel_id=channel_id,
                chat_id=chat_id,
                chat_history=chat_history
            ),
            self.media_handler_repo.delete(chat_id=chat_id)
        )
        solution = ""
        match (result_history, result_media):
            case (False, Error() as err):
                string_key = LangKey.RESET_MUL_ERROR
            case (False, Success()):
                string_key = LangKey.RESET_HISTORY_FAIL
            case (True, Error() as err):
                #string_key = LangKey.RESET_MEDIA_HIS_FAIL
                string_key = LangKey.RESET_HIS_DONE
            case (True, Success()):
                string_key = LangKey.RESET_HIS_DONE
                solution = ""

        translated_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=string_key,
            lan_code=lan_code
        )
        return translated_msg, solution