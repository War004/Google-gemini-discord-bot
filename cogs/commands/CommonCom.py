import discord

from discord.ext import commands
from charset_normalizer import from_bytes
from discord import app_commands
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.PersonaRepo import PersonaRepo
from translator.Translator import Translator
from BloomFilter import BloomFilter

from loader.Results import *
from utils.PngParserResults import PngParserResults

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
from cogs.chat.ChatHistoryHandler import ChatHistoryHandler
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
            lan_map: dict[str,dict[str,str]],
            translator: Translator,
            chat_history_manager: ChatHistoryHandler,
            channel_config_repo: ChannelConfigRepo,
            webhook_repo: WebhookInfoRepo
    ):
        self.bot = bot
        self.bot_system_ins_token = 9992
        self.main_bot_sys = main_bot_sys
        self.language = lan_map
        self.translator = translator
        self.self_history_manager = chat_history_manager
        self.channel_repo = channel_config_repo
        self.webhook_repo = webhook_repo
    
    """
    3 commands in total,
    check token,
    ping defer,
    info
    """

    def getTranslation(self,key:str,default:str,lan_code:str) ->str:
        ignore_list = set()
        if(lan_code in ignore_list): return #silent return

        string_dict = self.language.get(lan_code,None)

        if(string_dict == None ):
            print("The lan_code is not present.")
            return default
        
        return string_dict.get(key,default)
    
    async def create_webhook_dropdown(self, interaction: discord.Interaction, placeholder: str, callback):

        lan_code = await self.translator.get_lan_code_slash(
            server_id = str(interaction.guild.id) if interaction.guild else f"dm_{interaction.channel_id}",
            channel_id=str(interaction.channel_id),
            user_locale=interaction.locale
        )

        
        if isinstance(interaction.channel, discord.DMChannel):
            return

        try:
            #get all webhook
            webhooks = await interaction.channel.webhooks()
            bot_webhook = []

            if len(webhooks) < 1 or webhooks is None:
                await interaction.followup.send(self.getTranslation(0,"No webhook found in this channel",lan_code))
                return
            #start the loop to delete
            webhooks:list[Webhook] = await interaction.channel.webhooks()

            for webhook in webhooks:
                if(webhook.user == self.bot.user):
                    bot_webhook.append(webhook)

            #add the options,
            #10 webhooks are the limit far more then 25 item in discord list
            options = [
                discord.SelectOption(label=self.bot.user.name, value="main_bot_"),
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
                    await interaction.followup.send(self.getTranslation(0,f"No permission to manage webhooks in {interaction.channel.name}.", lan_code))
                case discord.HTTPException:
                    await interaction.followup.send(self.getTranslation(0,"An HTTP error occurred while fetching webhooks.", lan_code))
                case _:
                    await interaction.followup.send(self.getTranslation(0,"An unexpected error occurred while generating the webhook list.", lan_code))
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

        lan_code = await self.translator.get_lan_code_slash(
            server_id = str(interaction.guild.id) if interaction.guild else f"dm_{interaction.channel_id}",
            channel_id=interaction.channel_id,
            user_locale=interaction.locale
        )

        if isinstance(interaction.channel, discord.DMChannel):
            #get the channel details
            results = await self.channel_repo.get(str(interaction.channel_id))

            match results:
                case Error():
                    await interaction.followup.send(self.getTranslation(0,"Something happened while fetching channel config from db",lan_code))
                    return
            
            data = results.data

            if data is None:
                await interaction.followup.send(self.getTranslation(0,"Channel not configured",lan_code))
                return
            
            if data.api_key is None:
                await interaction.followup.send(self.getTranslation(0,"APi key is empty.",lan_code))
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

                await interaction.followup.send(self.getTranslation(0,f"Total token used: {total_token}", lan_code))

            except Exception as e:
                await interaction.followup.send(self.getTranslation(0, "An error occurred while counting tokens.", lan_code))
                print(f"[check_token] Exception: {e}")
                return
        else:
            async def select_callback(select_interaction: discord.Interaction):
                await select_interaction.response.defer()
                selected_value = select_interaction.data["values"][0]
                
                results = await self.channel_repo.get(str(select_interaction.channel_id))
                match results:
                    case Error():
                        await select_interaction.followup.send(self.getTranslation(0, "Something happened while fetching channel config from db", lan_code), ephemeral=True)
                        return
                    case _:
                        data = results.data
                
                if data is None or data.api_key is None:
                    await select_interaction.followup.send(self.getTranslation(0, "Channel not configured or API key is empty.", lan_code), ephemeral=True)
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
                        await select_interaction.followup.send(self.getTranslation(0, f"Total token used: {total_token}", lan_code))
                    except Exception as e:
                        await select_interaction.followup.send(self.getTranslation(0, "An error occurred while counting tokens.", lan_code), ephemeral=True)
                        print(f"[check_token] main_bot_ Exception: {e}")
                else:
                    webhook_id = int(selected_value)
                    webhook_res = await self.webhook_repo.get(webhook_id)
                    
                    match webhook_res:
                        case Error():
                            await select_interaction.followup.send(self.getTranslation(0, "Something happened while fetching webhook config from db", lan_code), ephemeral=True)
                            return
                    
                    info = webhook_res.data

                    
                    if info is None:
                        await select_interaction.followup.send(self.getTranslation(0, "Webhook is not configured.", lan_code), ephemeral=True)
                        return
                        
                    chat_history = await self.self_history_manager.load(
                        channel_id=str(select_interaction.channel_id),
                        chat_id = f"{webhook_id}_{select_interaction.channel_id}"
                    )
                    
                    system_info = info.webhook_system_information
                    
                    if len(chat_history) == 0:
                        await select_interaction.followup.send(self.getTranslation(0, "No history for this webhook.", lan_code), ephemeral=True)
                        return
                    if len(system_info) == 0:
                        await select_interaction.followup.send(self.getTranslation(0, "No system info found", lan_code), ephemeral=True)
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
                            
                        await select_interaction.followup.send(self.getTranslation(0, f"Total token used: {total_token}", lan_code))
                    except Exception as e:
                        await select_interaction.followup.send(self.getTranslation(0, "An error occurred while counting tokens.", lan_code), ephemeral=True)
                        print(f"[check_token] webhook Exception: {e}")

            view = await self.create_webhook_dropdown(interaction, self.getTranslation(0, "Select a bot to check token usage", lan_code), select_callback)
            if view:
                await interaction.followup.send(self.getTranslation(0, "Select a bot to check token usage:", lan_code), view=view) 
    
    @app_commands.command(
        name=app_commands.locale_str("info"),
        description=app_commands.locale_str("Get some basic info about the bot.")
    )
    async def get_info(self,interaction: discord.Interaction):

        await interaction.response.defer()

        lan_code = await self.translator.get_lan_code_slash(
            server_id = str(interaction.guild.id) if interaction.guild else f"dm_{interaction.channel_id}",
            channel_id=interaction.channel_id,
            user_locale=interaction.locale
        )

        channel_id = str(interaction.channel_id)
        channel_config = await self.channel_repo.get(channel_id)

        match channel_config:
            case Error():
                await interaction.followup.send(channel_config.message)
                return
        channel_data = channel_config.data

        string = f"\n```Api Key: {"Exists" if(channel_data.api_key) else "None"}\nDefault model: {channel_data.model_name}\nDefault language: {channel_data.default_lan_code}```\n"

        await interaction.followup.send(self.getTranslation(0,string,lan_code))
    @app_commands.command(
        name=app_commands.locale_str("ping"),
        description=app_commands.locale_str("Check the bot's latency.")
    )
    async def ping_defer(self, interaction: discord.Interaction):

        await interaction.response.defer()

        lan_code = await self.translator.get_lan_code_slash(
            server_id = str(interaction.guild.id) if interaction.guild else f"dm_{interaction.channel_id}",
            channel_id=interaction.channel_id,
            user_locale=interaction.locale
        )

        latency = round(self.bot.latency * 1000)
        await interaction.followup.send(self.getTranslation(0, f"Pong! Bot latency is {latency}ms.", lan_code))