import discord
from discord import app_commands
from discord import Embed
from discord import ui
from discord import ButtonStyle
from discord import HTTPException
from discord.app_commands.errors import CommandInvokeError
from discord import Locale
from discord.ext import commands
from google import genai
from google.genai import types
from google.genai.types import Content, Part
import sys
import traceback
import os
import json
import pickle
import re
import requests
import base64
import io
import PIL.Image
import shutil
import asyncio
import aiohttp
import asyncio
import aiofiles
import warnings
import time

from PIL import Image
from pixiv import *
from utilsNew import load_api_keys, model_Loader, save_api_json, extract_response_text, modify_history, api_Checker


#language dictionary
with open("commandsTrimeed.json", "r", encoding="utf-8") as f: # Ensure UTF-8 encoding!
    command_translations = json.load(f)
language_to_locale = {
    "en": "en-US",
    "hi": "hi",
    "ru": "ru",
    "ja": "ja",
    "fr": "fr",
}
#----//----#
class SlashCommandHandler:
    def __init__(self, bot,client, model_name, config, 
                 system_instruction, webhooks, bot_webhook_ids, api_keys, GOOGLE_API_KEY,
                 get_channel_directory, get_bot_paths, 
                 load_chat_history, save_chat_history, check_expired_files,
                 load_webhook_system_instruction,send_message_webhook,get_language_dict,wait_for_file_activation,save_filetwo):
        self.bot = bot
        self.cilent = client #replaced self.model = model
        self.model_name = model_name
        self.config = config
        self.system_instruction = system_instruction
        self.webhooks = webhooks
        self.bot_webhook_ids = bot_webhook_ids
        self.PHPSESSID = None
        self.api_keys = api_keys # Initialize the api_keys dictionary
        self.GOOGLE_API_KEY = GOOGLE_API_KEY
        
        # Store utility functions
        self.get_channel_directory = get_channel_directory
        self.get_bot_paths = get_bot_paths
        self.load_chat_history = load_chat_history
        self.save_chat_history = save_chat_history
        self.check_expired_files = check_expired_files
        self.load_webhook_system_instruction = load_webhook_system_instruction
        self.send_message_webhook = send_message_webhook
        self.get_language_dict = get_language_dict
        self.wait_for_file_activation = wait_for_file_activation
        self.save_filetwo = save_filetwo

    async def get_lan(self, interaction: discord.Interaction):
        """
        Retrieves the appropriate language dictionary for the given interaction.

        Args:
            interaction (discord.Interaction): The interaction object.

        Returns:
            dict: The language dictionary for the channel.
        """
        channel_id = str(interaction.channel.id)
        result = await api_Checker(self.api_keys, channel_id)  # Use your api_Checker
        if result:
            _, _, laCode = result
            return self.get_language_dict(laCode)
        else:
            return self.get_language_dict("en")  # Default to English

    async def create_webhook_dropdown(self, interaction: discord.Interaction, placeholder: str, callback):
        """Creates a dropdown menu with available webhooks."""

        lan = await self.get_lan(interaction)
        # Get all webhooks in the channel
        webhooks = await interaction.channel.webhooks()

        # Filter out the webhooks created by the bot
        bot_webhooks = [webhook for webhook in webhooks if webhook.user == self.bot.user]

        if not bot_webhooks:
            await interaction.followup.send(lan["slaErrorNoWebHook"])
            return None

        # Create a dropdown menu with the webhook names
        options = [
            discord.SelectOption(label=self.bot.user.name, value="main_bot"),
            *[discord.SelectOption(label=webhook.name, value=str(webhook.id)) for webhook in bot_webhooks]
            ]
        view = discord.ui.View()
        dropdown = discord.ui.Select(
            placeholder=placeholder,
            options=options
        )
        dropdown.callback = callback
        view.add_item(dropdown)

        return view

    async def setup_slash_commands(self):
        @self.bot.tree.command(
            name="test",
            description="A simple test command"
        )
        async def test_command(interaction: discord.Interaction):
            lan = await self.get_lan(interaction)
            await interaction.response.send_message(lan["slaTest"], ephemeral=False)
            print("test command used!")

        ###WARNING THIS IS NOT WORKING!!!!###
        """
        @self.bot.tree.command(name="check_token_usage", description="Check the token usage")
        async def check_token_usage(interaction: discord.Interaction):
            await interaction.response.defer()  # Defer the response as this might take a while
            print("check_token_usage command used!")

            channel_dir = self.get_channel_directory(interaction)

            if isinstance(interaction.channel, discord.DMChannel):
                bot_id = "main_bot"  
                chat_history_path, time_files_path, _ = self.get_bot_paths(channel_dir, bot_id)

                history = self.load_chat_history(chat_history_path)
                chat_history = self.check_expired_files(time_files_path, history,chat_history_path)
                chat = self.model.start_chat(history=chat_history)
                token_count = self.model.count_tokens(chat.history)

                response = f"{token_count}"
                await interaction.followup.send(response)

            else:  # If in a channel, show a dropdown menu
                async def check_token_usage_callback(interaction: discord.Interaction):
                    selected_value = interaction.data['values'][0]

                    chat_history_path, time_files_path, _ = self.get_bot_paths(channel_dir, selected_value)

                    history = self.load_chat_history(chat_history_path)
                    chat_history = self.check_expired_files(time_files_path, history,chat_history_path)

                    if selected_value == "main_bot":
                        chat=client.aio.chats.create(
                            model=self.model_name,
                            config = types.GenerateContentConfig(
                                system_instruction=system_instruction
                            ),
                            history=chat_history
                        )
                        response = await chat.count_tokens()
                    else:
                        system_instruction = self.load_webhook_system_instruction(selected_value, channel_dir)
                        client = genai.Client(api_key=self.GOOGLE_API_KEY)

                        chat=client.aio.chats.create(
                            model=self.model_name,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction
                            ),
                            history=chat_history
                        )
                        response = await chat.count_tokens()

                    #token_count = self.model.count_tokens(chat.history)  # Use the global model for token counting
                    response = f"{token_count}"
                    await interaction.response.send_message(response)

                view = await self.create_webhook_dropdown(interaction, "Select a bot/webhook", check_token_usage_callback)
                if view:
                    await interaction.followup.send("Select a bot/webhook to check token usage:", view=view)
                else:
                    # If no webhooks, default to main_bot
                    bot_id = "main_bot"
                    chat_history_path, time_files_path, _ = self.get_bot_paths(channel_dir, bot_id)
                    history = self.load_chat_history(chat_history_path)
                    chat_history = self.check_expired_files(time_files_path, history,chat_history_path)
                    #chat = self.model.start_chat(history=chat_history)

                    response = client.models.count_tokens(
                        model='gemini-2.0-flash-exp',
                        contents='.',
                        history=chat_history
                    )
                    print(response)
                    #token_count = self.model.count_tokens(chat.history)
                    response = f"{response} (main_bot)"
                    await interaction.followup.send(response)
                    """

        @self.bot.tree.command(name="info", description="Displays bot information")
        async def info_command(interaction: discord.Interaction):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()  # Defer the response as it might take a bit

            # Get the bot's latency
            latency = self.bot.latency * 1000

            # Create an embed to display the information nicely
            embed = discord.Embed(title=lan["slaBotInfo"], color=discord.Color.blue())
            channel_id = str(interaction.channel.id)
            name_Model = await model_Loader(self.api_keys, channel_id)

            embed.add_field(name=lan["slaModelName"], value=name_Model, inline=False)
            embed.add_field(name=lan["slaPing"], value=f"{latency:.2f} ms", inline=False)

            # Create a temporary text file with the system instructions
            with open("system_instructions.txt", "w", encoding="utf-8") as f:
                f.write(self.system_instruction)

            # Send the embed and the text file as an attachment
            await interaction.followup.send(embed=embed, file=discord.File("system_instructions.txt"))

        @self.bot.tree.command(name="add_webhook", description="Adds a webhook to the channel with system instructions")
        @app_commands.describe(
            name="The name for the webhook",
            avatar="The avatar image for the webhook (png/jpg/webp, optional)",
            plain_text_instructions="System instructions as plain text (either this or text_file_instructions is required)",
            text_file_instructions="System instructions as a text file attachment (either this or plain_text_instructions is required)"
        )
        async def add_webhook_command(
            interaction: discord.Interaction,
            name: str,
            avatar: discord.Attachment = None,
            plain_text_instructions: str = None,
            text_file_instructions: discord.Attachment = None
        ):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()

            try:
                # Check if exactly one of plain_text_instructions or text_file_instructions is provided
                if (plain_text_instructions is None) == (text_file_instructions is None):
                    await interaction.followup.send(lan["slaFollowUpAddWebhook"])
                    return

                # Get system instructions
                if plain_text_instructions:
                    system_instructions = plain_text_instructions
                else:
                    # Check if the attachment is a text file
                    if not text_file_instructions.content_type.startswith("text/"):
                        await interaction.followup.send(lan["slaErrorAddWebhookEwText"])
                        return
                    system_instructions = (await text_file_instructions.read()).decode("utf-8")

                # Download the avatar image (if provided)
                avatar_bytes = None
                if avatar:
                    if avatar.content_type not in ["image/png", "image/jpeg", "image/webp"]:
                        await interaction.followup.send(lan["slaErrorAddWebhookEwImage"])
                        return
                    avatar_bytes = await avatar.read()

                # Create the webhook
                webhook = await interaction.channel.create_webhook(name=name, avatar=avatar_bytes)

                # Store the webhook
                self.webhooks[webhook.id] = webhook

                # Store webhook data (webhook's user_id and system instructions) in a JSON file
                channel_dir = self.get_channel_directory(interaction)
                webhook_data_path = os.path.join(channel_dir, "webhooks", f"{webhook.id}_data.json")

                os.makedirs(os.path.dirname(webhook_data_path), exist_ok=True) # Create directory if it doesn't exist

                webhook_data = {
                    "webhook_user_id": webhook.id,  # Capturing the webhook's user_id
                    "system_instructions": system_instructions
                }

                with open(webhook_data_path, "w") as f:
                    json.dump(webhook_data, f, indent=4)
                self.bot_webhook_ids.add(webhook.id) #orginal format

                await interaction.followup.send(f"{lan['webhook']} '{name}' {lan['slaAddWebhookSuccFollowUp']}")
                await webhook.send(lan["slaReadyWebhook"])

            except discord.HTTPException as e:
                await interaction.followup.send(f"{lan['slaAddwebError']}{e}")

        @self.bot.tree.command(name="remove_webhook", description="Removes a webhook created by the bot")
        async def remove_webhook_command(interaction: discord.Interaction):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()

            async def remove_webhook_callback(interaction: discord.Interaction):
                selected_value = interaction.data['values'][0]  # Get the selected webhook ID from interaction.data

                channel_dir = self.get_channel_directory(interaction)
                webhook_data_path = os.path.join(channel_dir, "webhooks", f"{selected_value}_data.json")
                webhook_file_path = os.path.join(channel_dir,f"{selected_value}/")

                try:
                    # Fetch the webhook to ensure it still exists before deleting
                    webhook_to_delete = await self.bot.fetch_webhook(int(selected_value))

                    if webhook_to_delete:
                        await webhook_to_delete.delete()

                        # Remove webhook data file
                        if os.path.exists(webhook_data_path): #logically if one exists the other will also exist
                            os.remove(webhook_data_path)
                            shutil.rmtree(webhook_file_path)

                        await interaction.response.send_message(f"{lan['webhook']} '{webhook_to_delete.name}' {lan['removedSuccessfully']}")
                    else:
                        await interaction.response.send_message(lan["webhookNotFound"])

                except discord.NotFound:
                    # Handle the case where the webhook is not found
                    await interaction.response.send_message(lan["webAlreadydeleted"])
                    if os.path.exists(webhook_data_path):
                        os.remove(webhook_data_path)
                except discord.HTTPException as e:
                    await interaction.response.send_message(f"{lan['webErrorRemove']}{e}")

            view = await self.create_webhook_dropdown(interaction, lan["selectToRemove"], remove_webhook_callback)
            if view:
                await interaction.followup.send(lan["selectToRemove"], view=view)


        @self.bot.tree.command(name="remove_all_webhooks", description="Removes all webhooks created by the bot in the channel")
        async def remove_all_webhooks_command(interaction: discord.Interaction):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()

            try:
                # Get all webhooks in the channel
                webhooks = await interaction.channel.webhooks()

                # Filter out the webhooks created by the bot
                bot_webhooks = [webhook for webhook in webhooks if webhook.user == self.bot.user]

                if not bot_webhooks:
                    await interaction.followup.send(lan["noWebhookInchannel"])
                    return

                # Delete each webhook and remove data files
                channel_dir = self.get_channel_directory(interaction)
                for webhook in bot_webhooks:
                    await webhook.delete()
                    webhook_data_path = os.path.join(channel_dir, "webhooks", f"{webhook.id}_data.json")
                    webhook_file_path = os.path.join(channel_dir, f"{webhook.id}/") # Corrected line
                    if os.path.exists(webhook_data_path):
                        os.remove(webhook_data_path)
                        shutil.rmtree(webhook_file_path)

                    """bot_id = str(webhook.id)
                    chat_history_path, _, _ = self.get_bot_paths(channel_dir, bot_id)
                    with open(chat_history_path, 'wb') as file:
                        pickle.dump([], file)  # Empty the file
                    os.rename(chat_history_path, os.path.join(os.path.dirname(chat_history_path), "deleted.pkl"))"""


                await interaction.followup.send(lan["allRemove"])

            except discord.HTTPException as e:
                await interaction.followup.send(f"{lan['webErrorRemove']}{e}")

        @self.bot.tree.command(name="clear_webhook_messages", description="Deletes all messages in a channel sent by webhooks created by this bot.")
        @commands.has_permissions(manage_messages=True)
        async def clear_webhook_messages(interaction: discord.Interaction, channel: discord.TextChannel = None):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()

            if channel is None:
                channel = interaction.channel

            deleted_messages = 0
            async for message in channel.history(limit=500):
                if message.webhook_id is not None:
                    try:
                        webhook = await self.bot.fetch_webhook(message.webhook_id)
                        if webhook.user == self.bot.user:
                            await message.delete()
                            deleted_messages += 1
                    except discord.NotFound:
                        pass

            await interaction.followup.send(f"{lan['deleted']} {deleted_messages} {lan['clearWebMes']} {channel.mention}.")


        @self.bot.tree.command(name="reset_chat_history", description="Resets the chat history for the selected bot/webhook")
        async def reset_chat_history(interaction: discord.Interaction):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()  # Defer the response as this might take a while
            print("reset_chat_history command used!")

            channel_dir = self.get_channel_directory(interaction)

            async def reset_specific_chat(channel_dir: str, bot_id: str, is_image: bool, interaction: discord.Interaction, webhook_name: str = None):
                if is_image:
                    # Image chat history paths
                    chat_history_path, times_path_file, _ = self.get_bot_paths(channel_dir, bot_id, is_image_chat=True)
                else:
                    # Regular chat history paths
                    chat_history_path, times_path_file, _ = self.get_bot_paths(channel_dir, bot_id)
                
                try:
                    # Reset chat history
                    history = self.load_chat_history(chat_history_path)
                    if bot_id == "main_bot":
                        history = []
                    else:
                        messageIndex = [0,1,2,3,4,5]
                        history = modify_history(history, messageIndex)

                    async with aiofiles.open(chat_history_path, 'wb') as file:
                        await file.write(pickle.dumps(history))
                    
                    async with aiofiles.open(times_path_file, 'w') as file:
                        await file.write('[]')
                        
                    history_type = "image chat history" if is_image else "regular chat history"
                    print(f"Reset {history_type} for {bot_id}")
                    return True
                        
                except Exception as e:
                    print(f"Error resetting {'image' if is_image else 'regular'} chat history: {e}")
                    return False

            if isinstance(interaction.channel, discord.DMChannel):
                bot_id = "main_bot"
                # Reset both regular and image chat history for DMs
                reg_success = await reset_specific_chat(channel_dir, bot_id, False, interaction)
                img_success = await reset_specific_chat(channel_dir, bot_id, True, interaction)
                await interaction.followup.send(lan["chatResetMainBot"])

            else:  # If in a channel, show a dropdown menu
                async def reset_chat_history_callback(interaction: discord.Interaction):
                    try:
                        # Defer the response immediately to prevent interaction timeout
                        await interaction.response.defer(ephemeral=True)
                        
                        selected_value = interaction.data['values'][0]
                        
                        # Parse the selected value to determine if it's image history
                        is_image = False
                        if "[Img]" in selected_value:
                            is_image = True
                            bot_id = selected_value.replace("[Img]", "")
                        else:
                            bot_id = selected_value
                        
                        webhooks = await interaction.channel.webhooks()
                        webhook_dict = {str(webhook.id): webhook for webhook in webhooks}
                        
                        webhook_name = None
                        if bot_id != "main_bot" and bot_id in webhook_dict:
                            webhook_name = webhook_dict[bot_id].name

                        success = await reset_specific_chat(channel_dir, bot_id, is_image, interaction, webhook_name)
                        
                        message = lan["chatResetMessage"] if success else lan["chatReset"]
                        history_type = "image chat history" if is_image else "regular chat history"
                        
                        if bot_id == "main_bot":
                            await interaction.followup.send(f"{message} (main bot - {history_type})")
                        else:
                            bot_name = webhook_dict[bot_id].name if bot_id in webhook_dict else bot_id
                            await interaction.followup.send(f"{message} (webhook: {bot_name} - {history_type})")

                    except discord.NotFound:
                        try:
                            await interaction.channel.send(lan['chatResetTimeoutbSucc'])
                        except:
                            print("Failed to send timeout message")
                    except Exception as e:
                        print(f"Error in reset_chat_history_callback: {e}")
                        try:
                            await interaction.followup.send(lan["chatResetError"])
                        except:
                            try:
                                await interaction.channel.send(lan["chatResetError"])
                            except:
                                print("Failed to send error message")

                # Updated create_enhanced_webhook_dropdown function with shorter descriptions
                # and image option only for main bot
                async def create_enhanced_webhook_dropdown(interaction, placeholder, callback):
                    # Get webhooks in the channel
                    webhooks = await interaction.channel.webhooks()
                    options = []
                    
                    # Add main bot options (both regular and image)
                    options.append(discord.SelectOption(
                        label="Main Bot (Regular Chat)",
                        value="main_bot",
                        description="Reset regular chat history"
                    ))
                    options.append(discord.SelectOption(
                        label="Main Bot (Image Chat)",
                        value="main_bot[Img]",
                        description="Reset image chat history"
                    ))
                    
                    # Add webhook options (only regular chat, no image option)
                    for webhook in webhooks:
                        if webhook.user and webhook.user.id == self.bot.user.id:
                            # Only add regular chat history option for webhooks
                            options.append(discord.SelectOption(
                                label=f"{webhook.name} (Regular Chat)",
                                value=str(webhook.id),
                                description="Reset regular chat history"
                            ))
                    
                    if not options:
                        return None
                        
                    # Create the dropdown
                    select = discord.ui.Select(
                        placeholder=placeholder,
                        min_values=1,
                        max_values=1,
                        options=options
                    )
                    select.callback = callback
                    
                    view = discord.ui.View()
                    view.add_item(select)
                    return view
                        
                view = await create_enhanced_webhook_dropdown(interaction, "Select a bot/webhook", reset_chat_history_callback)
                if view:
                    await interaction.followup.send("Select which chat history to reset:", view=view)
                else:
                    # If no webhooks are found, don't automatically reset - just inform the user
                    await interaction.followup.send("No chat histories available to reset in this channel.")

        @self.bot.tree.command(name="add_v2_card_characters", description="Adds a V2 card character using a PNG file")
        @app_commands.describe(
            image="The PNG image file containing the character data (required)"
        )
        async def add_v2_card_characters(
            interaction: discord.Interaction,
            image: discord.Attachment
        ):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()

            try: 
                # Attempt to refresh the attachment data
                """try:
                    print(f"interaction.message: {interaction.message}")
                    refreshed_message = await interaction.channel.fetch_message(interaction.message.id)
                    refreshed_image = next((a for a in refreshed_message.attachments if a.id == image.id), None)
                    if refreshed_image:
                        image = refreshed_image
                except (discord.NotFound, AttributeError):
                    # If we can't refresh, we'll use the original attachment
                    pass"""
                # Check if the attachment is a PNG file
                if not image.content_type == "image/png":
                    await interaction.followup.send(lan["v2EwImage"])
                    return

                # Download the image
                image_bytes = await image.read()

                # Open the image using PIL
                img = PIL.Image.open(io.BytesIO(image_bytes))

                # Extract the metadata
                meta_data = img.text

                # Extract and decode the base64 string
                #print("Metadata keys:", meta_data.keys())
                base64_message = meta_data.get('chara', '')
                if not base64_message:
                    await interaction.followup.send(lan["v2Nochara"])
                    return

                extracted_text = base64.b64decode(base64_message).decode('utf-8')

                try:
                    data_dict = json.loads(extracted_text)
                    #print(data_dict)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON string")
                    await interaction.followup.send(lan["v2ImageError"])
                    return

                # Check if 'data' key exists, if not use the entire dictionary
                character_data = data_dict.get('data', data_dict)

                # Safely get values with default empty strings
                name = character_data.get('name', '')[:80]
                description = f"{lan['v2Descrpi']} {name} {lan['v2Descrpi1']}" + character_data.get('description', '') + lan["v2Descrpi2"]
                scenario = f"{lan['v2Scenario']}{name} {lan['is']} " + character_data.get('scenario', '') + lan["v2Scenario1"]
                system_prompt = f"{lan['v2SystemPro']}" + character_data.get('system_prompt', '') + lan["v2SystemPro1"]
                message_example = lan["v2MessageEx"] + character_data.get('mes_example', '') + lan["v2MessageEx1"]

                name_ins = f'{lan["v2nameIns"]} "{name}" {lan["v2nameIns1"]} {name} {lan["v2nameIns2"]}'

                user_id = interaction.user.id
                greeting = character_data.get('first_mes', '')
                greeting = re.sub(r'{{\s*user\s*}}', f'<@{user_id}>', greeting, flags=re.IGNORECASE)
                greeting = re.sub(r'{{\s*char\s*}}', f'{name}', greeting, flags=re.IGNORECASE)
                processed_instructions = f"{system_prompt}\n{name_ins}\n{description}\n{scenario}\n{message_example}"

                system_break_ins = "."
                
                final_instruction = system_break_ins + processed_instructions

                # Create the webhook with the image as the avatar
                webhook = await interaction.channel.create_webhook(name=name, avatar=image_bytes)

                # Store the webhook
                self.webhooks[webhook.id] = webhook

                # Get the channel directory and file paths
                channel_dir = self.get_channel_directory(interaction)
                bot_id = str(webhook.id)
                self.bot_webhook_ids.add(webhook.id) #orginal format
                chat_history_path, time_files_path, attachments_dir = self.get_bot_paths(channel_dir, bot_id)

                # Create the custom model
                channel_id = str(interaction.channel.id)
                client = genai.Client(api_key=self.GOOGLE_API_KEY)
                ##genai.configure(api_key=self.GOOGLE_API_KEY) #default
                name_Model = await model_Loader(self.api_keys, channel_id)
                
                
                system_instruction = f" {lan['v2systemIns']} {final_instruction}. {lan['v2systemIns1']}"  # Or any other default instruction you want
                #print(f'This is the starting\n{final_instruction}\n This is the ending')
                """
                custom_model = genai.GenerativeModel(
                    model_name=name_Model,
                    generation_config=self.text_generation_config,
                    system_instruction=system_instruction,
                    safety_settings=self.safety_settings,
                    tools="code_execution"
                )
                """

                # Create the initial prompt
                intial_prompt = [
            Content(role="user", parts=[Part(text=lan["v2InitialProUser"])]),
            Content(role="model", parts=[Part(text=lan["v2InitialProModel"])]),
            Content(role="user", parts=[Part(text=f"""{lan['v2InitialProUser1']}
                                {lan['write']} {name} {lan['response']} {name} {lan['response1']}
                                1. {lan['v2InitalProUser2']} {name} {lan['v2InitalProUser21']} {name} {lan['v2InitalProUser22']} <@{user_id}>.
                                2. {lan['v2InitalProUser3']}
                                3. {lan['v2InitalProUser4']} <@{user_id}> {lan['v2InitalProUser41']} {name} {lan['v2InitalProUser42']}
                                4. {lan['v2InitalProUser5']}
                                5. {lan['v2InitalProUser6']}
                                {lan['v2InitalProUser61']}
                                {lan['v2InitalProUser62']}
                                {lan['v2InitalProUser63']} """)]),
            Content(role="user", parts=[Part(text=lan['v2InitalProUser7'])]),
            Content(role="model", parts=[Part(text=lan["v2InitalProModel2"])]),
            Content(role="model", parts=[Part(text=greeting)])
        ]

                # Start the chat and save the initial history
                # Get the channel directory and file paths
                if name_Model == "models/gemini-2.0-flash-exp":
                    blockValue = "OFF"
                else:
                    blockValue = "BLOCK_NONE"
                chat = client.aio.chats.create(
                    model=name_Model,
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=1,
                        top_p=0.95,
                        top_k=20,
                        candidate_count=1,
                        seed=-1,
                        max_output_tokens=8192,
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
                    history=intial_prompt,
                )

                print("Started generating responses")
                async_response = await chat.send_message(lan["v2InitalProUser8"])
                print(async_response.text)
                #print(await extract_response_text(async_response))
                self.save_chat_history(chat_history_path, chat)

                # Store webhook data (webhook's user_id and extracted text as system instructions) in a JSON file
                webhook_data_path = os.path.join(channel_dir, "webhooks", f"{webhook.id}_data.json")
                os.makedirs(os.path.dirname(webhook_data_path), exist_ok=True) 

                webhook_data = {
                    "webhook_user_id": webhook.id,
                    "system_instructions": processed_instructions
                }

                async with aiofiles.open(webhook_data_path, "w") as f:
                    await f.write(json.dumps(webhook_data, indent=4))

                await interaction.followup.send(f"{lan['character']} '{name}' {lan['v2Succ']}")
                #print("Greetings:")
                #print(greeting)
                await self.send_message_webhook(webhook=webhook, response=greeting) 

            except discord.HTTPException as e:
        # If webhook creation or any following steps fail, send an error message
                await interaction.followup.send(f"{lan['v2ErrorAdd']} {e}")
                
                # Attempt to delete the webhook only if it was successfully created
                try:
                    if 'webhook' in locals():
                        await webhook.delete()
                except discord.HTTPException as e:
                    print(f"{lan['v2ErrorDel']} {e}")
            
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = exc_tb.tb_frame.f_code.co_filename
                line_no = exc_tb.tb_lineno
                await interaction.followup.send(f"{lan['unexpectedError']} {e}\n\n```Error Details:\nType: {exc_type.__name__}\nMessage: {str(e)}\nFile: {fname}\nLine Number: {line_no}\nFull Traceback:{traceback.format_exc()}```")
                # Delete the webhook if created and an unexpected error occurs
                print(f"""Error Details:
                    Type: {exc_type.__name__}
                    Message: {str(e)}
                    File: {fname}
                    Line Number: {line_no}
                    Full Traceback: 
                    {traceback.format_exc()}""")
                try:
                    if 'webhook' in locals():
                        await webhook.delete()
                except discord.HTTPException as e:
                    print(f"{lan['v2ErrorDel']} {e}")

        @self.bot.tree.command(name="remove_all_except", description="Removes all webhooks created by the bot in the channel except the specified one")
        async def remove_all_except_command(interaction: discord.Interaction):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()

            async def remove_all_except_callback(interaction: discord.Interaction):
                selected_value = interaction.data['values'][0]  # Get the selected webhook ID

                # Delete all webhooks EXCEPT the selected one
                deleted_count = 0
                channel_dir = self.get_channel_directory(interaction)
                webhooks = await interaction.channel.webhooks()
                webhook_name = ""
                for webhook in webhooks:
                    if str(webhook.id) != selected_value:  # Compare with the selected webhook ID
                        try:
                            await webhook.delete()
                            deleted_count += 1
                            webhook_data_path = os.path.join(channel_dir, "webhooks", f"{webhook.id}_data.json")
                            webhook_file_path = os.path.join(channel_dir,f"{webhook.id}/")
                            if os.path.exists(webhook_data_path):
                                os.remove(webhook_data_path)
                                shutil.rmtree(webhook_file_path)
                        except discord.NotFound:
                            pass  # Webhook might have already been deleted
                    else:
                        webhook_name = webhook.name

                if deleted_count == 0:
                    await interaction.followup.send(f"{lan['removeExepctone']} '{webhook_name}'.")
                else:
                    await interaction.followup.send(f"All webhooks except '{webhook_name}' {lan['haveBeenRemoved']}")

            view = await self.create_webhook_dropdown(interaction, lan["selectToKeep"] , remove_all_except_callback)
            if view:
                await interaction.followup.send(lan["selectToKeep"], view=view)

        @self.bot.tree.command(name="edit_or_generate_image", description="Generate or edit images with Gemini Vision")
        @app_commands.describe(
            prompt="The text prompt for image generation or editing",
            image="Optional image to edit or use as context"
        )
        async def edit_or_generate_image_command(interaction: discord.Interaction, prompt: str, image: discord.Attachment = None):
            lan = await self.get_lan(interaction)  # Get language
            await interaction.response.defer()
            
            # List to capture warnings
            captured_warnings = []
            
            # Define a custom showwarning function to capture warnings
            def capture_warning(message, category, filename, lineno, file=None, line=None):
                captured_warnings.append(f"Warning: {message}")
                # Also show the warning in console for debugging
                original_showwarning(message, category, filename, lineno, file, line)
            
            # Save the original function to restore later
            original_showwarning = warnings.showwarning
            # Set our custom function
            warnings.showwarning = capture_warning

            channel_id = str(interaction.channel.id)
            channel_dir = self.get_channel_directory(interaction)
            bot_id = "main_bot"  # For main bot commands
            # Corrected call to get_bot_paths:
            chat_history_path, time_files_path, attachments_dir = self.get_bot_paths(channel_dir, bot_id, is_image_chat=True)

            history = self.load_chat_history(chat_history_path)
            chat_history = await self.check_expired_files(time_files_path, history, chat_history_path)

            # --- Get API Key ---
            result = await api_Checker(self.api_keys, channel_id)
            if not result:
                warnings.showwarning = original_showwarning  # Restore original warning handler
                await interaction.followup.send(lan["noInfomation"])
                return
            api_key, _, _ = result  # Only need the API key

            if not api_key:
                warnings.showwarning = original_showwarning  # Restore original warning handler
                await interaction.followup.send(lan["noInfomation"])
                return

            client = genai.Client(api_key=api_key)  # Use the retrieved API key
            model_name = "models/gemini-2.0-flash-exp"  # Hardcoded model

            try:
                image_config = types.GenerateContentConfig(
                    response_modalities=['Text', 'Image']
                )
                chat = client.aio.chats.create(
                    model=model_name,  # Use the hardcoded model
                    config=image_config,
                    history=chat_history,
                )

                parts = [prompt]  # Start with text prompt

                # Handle uploaded image if present
                if image:
                    image_mime = image.content_type
                    
                    # Create directory if it doesn't exist
                    os.makedirs(attachments_dir, exist_ok=True)
                    
                    # Save the image locally with timestamp to avoid name conflicts
                    timestamp = int(time.time())
                    safe_filename = ''.join(c for c in image.filename if c.isalnum() or c in '._-')
                    local_image_path = os.path.join(attachments_dir, f"{timestamp}_{safe_filename}")
                    
                    # Download and save the image
                    image_bytes = await image.read()
                    with open(local_image_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    print(f"Image saved to: {local_image_path}")
                    
                    # Upload the saved file to the client
                    with open(local_image_path, 'rb') as f:
                        file = await client.aio.files.upload(
                            file=f,
                            config=types.UploadFileConfig(mime_type=image_mime)
                        )
                    
                    file_uri = file.uri

                    # Create a media file part using the image URI
                    media_file = types.Part.from_uri(file_uri=file_uri, mime_type=image_mime)

                    status = await self.wait_for_file_activation(name=file.name, client=client)
                    if not status:
                        warnings.showwarning = original_showwarning  # Restore original warning handler
                        await interaction.followup.send(lan["errorNormalMediaActivation"])
                        return

                    # Save file info for tracking
                    message_index = len(chat_history) + 1  # Define message_index
                    self.save_filetwo(time_files_path, file_uri, message_index)

                    """if os.path.exists(local_image_path):
                        os.remove(local_image_path)
                        print(f"Deleted temporary file: {local_image_path}")"""
                    
                    # Update prompt to indicate image editing
                    prompt_text = f"Edit this image according to: {prompt}"
                    response = await chat.send_message([prompt_text, media_file])
                
                else: 
                    # Make the actual API call to generate the response
                    response = await chat.send_message(parts)
                
                # Extract the text and image data from the response
                response_text, image_data = await extract_response_text(response)
                
                # Save the updated chat history
                self.save_chat_history(chat_history_path, chat)

                # Now process the image data if it exists
                if image_data:
                    # Debug logging to understand the format
                    print(f"Image data format: {type(image_data)} - {len(image_data)} items")
                    
                    # Create discord.File objects from the (mime_type, image_bytes) tuples
                    discord_files = []
                    image_counter = 1
                    
                    for mime_type, image_bytes in image_data:
                        try:
                            # Extract file extension from mime type
                            ext = mime_type.split('/')[-1]
                            if ext == 'jpeg': ext = 'jpg'  # Normalize extension
                            
                            # Create filename
                            filename = f"generated_image_{image_counter}.{ext}"
                            image_counter += 1
                            
                            # Check if image_bytes is valid
                            if image_bytes and len(image_bytes) > 100:  # Minimum reasonable size for an image
                                file_obj = discord.File(io.BytesIO(image_bytes), filename=filename)
                                discord_files.append(file_obj)
                                print(f"Created Discord file for {filename}, size: {len(image_bytes)} bytes")
                            else:
                                print(f"Skipping small/invalid image data: {len(image_bytes)} bytes")
                        except Exception as e:
                            print(f"Error processing image: {str(e)}")
                    
                    # Prepare the response content
                    # Add captured warnings to the response if any
                    if captured_warnings:
                        warnings_text = "\n\n**Warnings detected:**\n" + "\n".join(captured_warnings)
                        if response_text:
                            response_text += warnings_text
                        else:
                            response_text = warnings_text
                    
                    # Ensure we have actual content to send
                    if response_text or discord_files:
                        if not response_text or response_text.strip() == "":
                            response_text = "Here's your generated image:" if discord_files else "I processed your request, but couldn't generate valid images."
                        
                        print(f"Sending response with {len(discord_files)} image(s)")
                        await interaction.followup.send(content=response_text, files=discord_files)
                    else:
                        # Fallback message if both text and files are empty or invalid
                        await interaction.followup.send(content="Sorry, I couldn't generate any valid content or images.")
                else:
                    # Make sure response_text is not None or empty
                    if not response_text or response_text.strip() == "":
                        response_text = "I processed your request, but there's no text or image to display."
                    
                    # Add captured warnings to the response if any
                    if captured_warnings:
                        response_text += "\n\n**Warnings detected:**\n" + "\n".join(captured_warnings)
                    
                    await interaction.followup.send(content=response_text)
            except Exception as e:
                error_message = f"Error processing request: {str(e)}"
                print(error_message)
                
                # Add any warnings that were captured before the exception
                if captured_warnings:
                    error_message += "\n\n**Warnings detected:**\n" + "\n".join(captured_warnings)
                
                await interaction.followup.send(content=error_message)
            finally:
                # Always restore the original warning handler
                warnings.showwarning = original_showwarning

        @self.bot.tree.command(name="change_model", description="Change the AI model")
        @app_commands.choices(
            model_names=[
                app_commands.Choice(name="Gemini 2.0 flash", value="models/gemini-2.0-flash"),
                app_commands.Choice(name="Gemini 2.0 flash exp[Text only]", value ="gemini-2.0-flash-exp-image-generation"),
                app_commands.Choice(name="Gemini 2.0 pro exp[05/02/2025]", value="models/gemini-2.0-pro-exp-02-05"),
                app_commands.Choice(name="Gemini 2.0 flash lite", value="models/gemini-2.0-flash-lite"),
                app_commands.Choice(name="Gemini 2.0 flash thinking[21/01/25]", value="models/gemini-2.0-flash-thinking-exp-01-21"),
                app_commands.Choice(name="Gemini 1.5 flash(latest)", value="models/gemini-1.5-flash-latest"),
                app_commands.Choice(name="Gemini 1.5 flash", value = "models/gemini-1.5-flash"),
                #app_commands.Choice(name="Gemini 1.5 flash(exp 0827)", value = "models/gemini-1.5-flash-exp-0827"),
                #app_commands.Choice(name="Gemini 1.5 flash(001)", value = "models/gemini-1.5-flash-001"),
                app_commands.Choice(name="Gemini 1.5 flash(002)", value = "models/gemini-1.5-flash-002"),
                app_commands.Choice(name="Gemini 1.5 flash(8b)(latest)", value = "gemini-1.5-flash-8b-latest"),
                app_commands.Choice(name="Gemini 1.5 pro(latest)", value = "models/gemini-1.5-pro-latest"),
                #app_commands.Choice(name="Gemini 1.5 pro(001)", value = "models/gemini-1.5-pro-001"),
                #app_commands.Choice(name="Gemini 1.5 pro(002)", value = "models/gemini-1.5-pro-002"),
                app_commands.Choice(name="Gemini 1.5 pro", value = "models/gemini-1.5-pro"),
                #app_commands.Choice(name="Gemini 1.5 pro(exp 0801)", value = "models/gemini-1.5-pro-exp-0801"),
                #app_commands.Choice(name="Gemini 1.5 pro(exp 0827)", value = "models/gemini-1.5-pro-exp-0827"),
                app_commands.Choice(name="Gemini 2.0 ...", value = "models/gemini-exp-1206"),
                app_commands.Choice(name="Learnlm 1.5 pro ", value = "models/learnlm-1.5-pro-experimental")
                
                
            ]
        )
        async def change_model_command(interaction: discord.Interaction, model_names: str):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()
            global model  # Access the global variables
            channel_id = str(interaction.channel.id)
            # Update the model with the selected model name
            if channel_id in self.api_keys:
                # Only update the model_name, leave the api_key unchanged
                self.api_keys[channel_id]["model_name"] = model_names
            else:
                # If the channel_id does not exist, create a new entry with just the model_name
                # Optionally: Set a default api_key if needed
                self.api_keys[channel_id] = {
                    "api_key": None,  # Replace this or leave it if API key is managed elsewhere
                    "model_name": model_names,
                    "language": None
                }

            # Save the updated api_keys dictionary
            await save_api_json(self.api_keys)

            if model_names == "models/learnlm-1.5-pro-experimental":
                message = (
                    f"{lan['modelChange']} {model_names}\n"
                    f"Learn llm has a lower context window 32767 so it may not work as perfectly. "
                    f"Change the model if it doesn't work."
                )
                await interaction.followup.send(message, ephemeral=False)

            if model_names == "models/gemini-exp-1206":
                message = (
                    f"{lan['modelChange']} {model_names}\n"
                    f"{lan['modelChangeexp1206']}"
                    f"{lan['modelChangeexp12061']}"
                )
                await interaction.followup.send(message, ephemeral=False)

            else:
                message = f"{lan['modelChange']} {model_names}"

                await interaction.followup.send(message, ephemeral=False)


        @self.bot.tree.command(name="set_language", description="Set the language for the bot")
        @app_commands.choices(
            language = [
                app_commands.Choice(name="Global (English) 🟩", value="en"),
                app_commands.Choice(name="India (অসমীয়া) 🟥", value="asS"),  # Assamese
                app_commands.Choice(name="India (বাংলা) 🟥", value="bn"),  # Bengali
                app_commands.Choice(name="India (ગુજરાતી) 🟥", value="gu"),  # Gujarati
                app_commands.Choice(name="India (हिन्दी) 🟥", value="hi"),  # Hindi
                app_commands.Choice(name="India (ಕನ್ನಡ) 🟥", value="kn"),  # Kannada
                app_commands.Choice(name="India (मैथिली) 🟥", value="mai"),  # Maithili
                app_commands.Choice(name="India (മലയാളം) 🟥", value="mal"),  # Malayalam
                app_commands.Choice(name="India (ꯃꯩꯇꯩ) 🟥", value="mni"),  # Meitei (Manipuri) - in Meitei Mayek script
                app_commands.Choice(name="India (मराठी) 🟥", value="mr"),  # Marathi
                app_commands.Choice(name="India (नेपाली) 🟥", value="ne"),  # Nepali
                app_commands.Choice(name="India (தமிழ்) 🟥", value="ta"),  # Tamil
                app_commands.Choice(name="Nepal (नेपाली) 🟥", value="ne"),  # Nepali
                app_commands.Choice(name="Russia (Русский) 🟥", value="ru"),  # Russian
                app_commands.Choice(name="Japan (日本語) 🟥", value="ja"),  # Japanese
                app_commands.Choice(name="French (Français) 🟥", value="fr"),  # French
            ]
        )
        async def set_language(interaction: discord.Interaction, language: app_commands.Choice[str]):
            lan = await self.get_lan(interaction)
            await interaction.response.defer()
            channel_id = str(interaction.channel_id)
            
            if channel_id in self.api_keys:
                self.api_keys[channel_id]['language'] = language.value
                
                # Save to JSON file
                await save_api_json(self.api_keys)
                    
                await interaction.followup.send(f"{language.name}")
            else:
                await interaction.followup.send("Channel not configured. Please set up API key first.") #Need to add in translation
        
        @self.bot.tree.command(name="start_roleplay",description="Display a list of character to start a new roleplay")
        async def start_roleplay(interaction: discord.Interaction):
            options = [
                discord.SelectOption(label = "Test",value="Placeholder"),
                discord.SelectOption(label = "Test2", value = "Placeholder2")
            ]
            view = discord.ui.View()
            dropdown = discord.ui.Select(
                placeholder = "Menu to select character",
                options = options
            )
            view.add_item(dropdown)

            await interaction.response.send_message("Select a character", view=view)
        
        @self.bot.tree.command(name="clone_user", description="[🚧]Clone a user's communication style")
        @app_commands.describe(
            target_user="Select the user to clone"
        )
        async def clone_user_command(interaction: discord.Interaction, target_user: discord.Member):
            """
            A Discord command that creates an AI-powered clone of a user's communication style.
            
            This function goes through several key steps:
            1. Defer the initial interaction response
            2. Create a webhook mimicking the target user
            3. Collect message history from the user
            4. Engineer a system prompt based on collected messages
            5. Initialize an AI chat session
            6. Send an initial message via webhook
            
            Args:
                interaction (discord.Interaction): The interaction context of the command
                target_user (discord.Member): The Discord member to be cloned
            """
            # Always defer the initial response to handle potentially long-running tasks
            await interaction.response.defer(ephemeral=True)
            
            # Get localization/language settings
            lan = await self.get_lan(interaction)

            async def create_message_collection_string(collected_messages, target_member_name):
                    """
                    Creates a comprehensive, readable string representation of collected messages
                    that captures context and conversation flow.
                    """
                    message_collection = f"Chat Session Analysis for {target_member_name}\n\n"
                    message_collection += "=" * 50 + "\n\n"

                    for index, entry in enumerate(collected_messages, 1):
                        target_msg = entry["target_user_message"]
                        context_before = entry["context_before"]
                        context_after = entry["context_after"]

                        message_collection += f"CONVERSATION SEGMENT {index}\n"
                        message_collection += "-" * 30 + "\n"

                        # Context Before
                        message_collection += "PRECEDING CONTEXT:\n"
                        for msg in context_before:
                            message_collection += f"[User {msg['author_id']} | {msg['timestamp']}]: {msg['content']}\n"
                        
                        # Target User's Message
                        message_collection += f"\n[{target_member_name} | {target_msg['timestamp']}]: {target_msg['content']}\n"
                        
                        # Reply Context (if applicable)
                        if target_msg.get('is_reply'):
                            message_collection += f"REPLY TO: {target_msg.get('reply_to_message_content', 'No original message found')}\n"
                        
                        # Context After
                        message_collection += "\nFOLLOWING CONTEXT:\n"
                        for msg in context_after:
                            message_collection += f"[User {msg['author_id']} | {msg['timestamp']}]: {msg['content']}\n"
                        
                        message_collection += "\n" + "=" * 50 + "\n\n"

                    return message_collection

            async def _create_clone_webhook(interaction: discord.Interaction, target_member: discord.Member):
                """
                Creates a webhook that mimics the target user's profile.
                
                This function handles:
                - Using the user's custom avatar or default avatar
                - Creating a webhook with the appropriate name and image
                
                Args:
                    interaction (discord.Interaction): The interaction context
                    target_member (discord.Member): The member whose profile is being cloned
                
                Returns:
                    discord.Webhook: The created webhook, or None if creation fails
                """
                try:
                    # Determine avatar to use
                    if target_member.avatar:
                        avatar_bytes = await target_member.avatar.read()
                    else:
                        # Fetch default avatar
                        async with aiohttp.ClientSession() as session:
                            async with session.get(target_member.default_avatar.url) as response:
                                avatar_bytes = await response.read()
                    
                    # Create webhook with user's name and avatar
                    webhook_name = f"Clone of {target_member.display_name}"
                    webhook = await interaction.channel.create_webhook(name=webhook_name, avatar=avatar_bytes)
                    return webhook
                
                except discord.HTTPException as e:
                    await interaction.followup.send(f"{lan['slaAddwebError']} {e}", ephemeral=True)
                    return None
                except Exception as e:
                    await interaction.followup.send(f"{lan['unexpectedError']} {e}", ephemeral=True)
                    return None

            async def _collect_user_messages(
                interaction: discord.Interaction, 
                target_user_id: int, 
                total_message_limit=200, 
                initial_scan_limit=10000, 
                context_window_size=10
            ):
                """
                Collects messages from the target user across all server channels with detailed progress tracking.
                
                Args:
                    interaction (discord.Interaction): The command interaction
                    target_user_id (int): ID of the user to clone
                    total_message_limit (int): Maximum number of user messages to collect
                    initial_scan_limit (int): Initial message scan limit per channel
                    context_window_size (int): Number of messages to collect before/after target messages
                
                Returns:
                    list: Collected messages with their surrounding context
                """
                collected_data = []
                message_counter = 0
                guild = interaction.guild
                total_channels = len(guild.text_channels)

                # Print overall start of collection
                print(f"\n--- Starting Message Collection ---")
                print(f"Target User ID: {target_user_id}")
                print(f"Total Channels to Scan: {total_channels}")
                print(f"Message Limit per Channel: {initial_scan_limit}")
                print(f"Total Message Limit: {total_message_limit}")
                print("-" * 50)

                await interaction.followup.send(lan["cloneStartCollectAllChannels"], ephemeral=False)

                for channel_index, channel in enumerate(guild.text_channels, 1):
                    if message_counter >= total_message_limit:
                        break

                    # Start of channel scanning progress
                    print(f"\nScanning Channel {channel_index}/{total_channels}: {channel.name} (ID: {channel.id})")
                    channel_message_count = 0

                    try:
                        async for message in channel.history(limit=initial_scan_limit, oldest_first=False):
                            if message_counter >= total_message_limit:
                                break
                            
                            if message.author.id == target_user_id:
                                message_entry = {
                                    "target_user_message": {
                                        "content": message.content,
                                        "author_id": str(message.author.id),
                                        "timestamp": str(message.created_at),
                                        "channel_name": channel.name,
                                        "channel_id": str(channel.id),
                                        "is_reply": message.reference is not None,
                                        "reply_to_message_content": None
                                    },
                                    "context_before": [],
                                    "context_after": []
                                }

                                # Handle reply context
                                if message_entry["target_user_message"]["is_reply"]:
                                    try:
                                        replied_message = await channel.fetch_message(message.reference.message_id)
                                        message_entry["target_user_message"]["reply_to_message_content"] = replied_message.content
                                    except:
                                        message_entry["target_user_message"]["reply_to_message_content"] = "<Replied message not found>"

                                # Collect context before message
                                context_before = []
                                async for before_msg in channel.history(limit=context_window_size, before=message, oldest_first=False):
                                    context_before.append({
                                        "content": before_msg.content,
                                        "author_id": str(before_msg.author.id),
                                        "timestamp": str(before_msg.created_at),
                                        "channel_name": channel.name,
                                        "channel_id": str(channel.id)
                                    })
                                message_entry["context_before"] = context_before

                                # Collect context after message
                                context_after = []
                                async for after_msg in channel.history(limit=context_window_size, after=message, oldest_first=True):
                                    context_after.append({
                                        "content": after_msg.content,
                                        "author_id": str(after_msg.author.id),
                                        "timestamp": str(after_msg.created_at),
                                        "channel_name": channel.name,
                                        "channel_id": str(channel.id)
                                    })
                                message_entry["context_after"] = context_after

                                collected_data.append(message_entry)
                                message_counter += 1 + (len(context_before) + len(context_after))
                                channel_message_count += 1

                                # Real-time progress update
                                print(f"  Progress: {channel_message_count} user messages found | Total: {message_counter}/{total_message_limit}")

                                if message_counter >= total_message_limit:
                                    break

                    except discord.Forbidden:
                        print(f"  [SKIPPED] Channel {channel.name} - Access Forbidden")
                    except Exception as channel_e:
                        print(f"  [ERROR] Processing {channel.name}: {channel_e}")

                    # Channel scanning completion
                    print(f"Completed Channel {channel_index}/{total_channels}: {channel_message_count} messages found")

                # Collection summary
                print("\n--- Message Collection Complete ---")
                print(f"Total Channels Scanned: {total_channels}")
                print(f"Total User Messages Collected: {message_counter}")
                print("-" * 50)

                return collected_data

            async def _engineer_prompt(collected_messages, target_member_name):
                """
                Creates a comprehensive system prompt for AI cloning.
                
                Transforms collected messages into a detailed instruction set
                that captures the user's communication style.
                
                Args:
                    collected_messages (list): Messages collected from the target user
                    target_member_name (str): Name of the user being cloned
                
                Returns:
                    str: Detailed system prompt for AI
                """
                # Use the previously discussed message collection string function
                message_collection_string = await create_message_collection_string(collected_messages, target_member_name)
                
                system_prompt_content = f"""
                You are roleplaying as {target_member_name}. 
                Your goal is to authentically mimic their unique communication style.

                COMMUNICATION STYLE GUIDELINES:
                - Analyze tone, sentiment, vocabulary, and interaction patterns
                - Maintain consistent persona across responses
                - Reflect genuine communication characteristics

                CONVERSATION CONTEXT:
                {message_collection_string}

                RESPONSE STRATEGY:
                1. Before responding, analyze the system message context
                2. Identify key communication traits
                3. Generate a response that sounds like {target_member_name}
                4. Maintain authenticity and context-awareness
                """
                return system_prompt_content

            try:
                # 1. Create Webhook
                webhook = await _create_clone_webhook(interaction, target_user)
                if not webhook:
                    return

                # 2. Collect User Messages
                await interaction.followup.send(lan["cloneStartCollect"], ephemeral=False)
                collected_messages = await _collect_user_messages(interaction, target_user.id)
                if not collected_messages:
                    await interaction.followup.send(lan["cloneNoMessages"], ephemeral=False)
                    await webhook.delete()
                    return

                # 3. Engineer Prompt
                await interaction.followup.send(lan["cloneEngineerPrompt"], ephemeral=False)
                system_prompt = await _engineer_prompt(collected_messages, target_user.display_name)

                # 4. Initialize AI Chat
                channel_dir = self.get_channel_directory(interaction)
                bot_id = str(webhook.id)
                self.bot_webhook_ids.add(webhook.id)

                client = genai.Client(api_key=self.GOOGLE_API_KEY)
                chat = client.aio.chats.create(
                    model="models/gemini-2.0-flash-thinking-exp-01-21",
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.9,
                        top_p=0.9,
                        max_output_tokens=65536,
                        safety_settings=[
                            types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold="BLOCK_NONE"),
                            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold="BLOCK_NONE"),
                            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold="BLOCK_NONE"),
                            types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold="BLOCK_NONE")
                        ]
                    ),
                    history=[]
                )

                # 5. Initialize Chat History
                chat_history_path, times_path_file, _ = self.get_bot_paths(channel_dir, bot_id)
                async_response = await chat.send_message("Analyze the system instructions and prepare to respond according to the user message. Now I will tell you how to genrate a response, so for now you will genrate a detalied anlyais of the target user by using the text in system instractions, you will genrate that will have eveything about the user that you can take out, think about the different user that are text and how is the target user responding to them are they frinedly or see other emoitons. You have a big context output so you don't have to worry about the lenght of the ouput in this message you have like 60k output tokens for this message you think as much as you can and first give the detalied planned about how you will try to mimcs the target but also make sure to be not 100 percent like the user be more like fliter for the target like a photo but with a very strong filter. And tell about your plans how will use the filter and after that you can create a list of all the user which were talking to the target user and tell how guess about there relation with the target user, so you could see like which user is currently is trying to talk and then you will refer to this table and see there relationship and then the apply the filter and then genrate the response. After this the message that would come to you would be expected a response as target reponse so make sure to make your filter of gemini to 0 and to target user to 100percent")
                self.save_chat_history(chat_history_path, chat)
                print(async_response.text)

                # 6. Send Initial Webhook Message
                await interaction.followup.send(lan["cloneReadyChat"], ephemeral=False)
                initial_message = f"Starting chat as a clone of {target_user.display_name}. Feel free to interact!"
                await self.send_message_webhook(webhook=webhook, response=initial_message)

            except Exception as e:
                # Comprehensive error handling
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = exc_tb.tb_frame.f_code.co_filename
                line_no = exc_tb.tb_lineno
                
                error_message = (
                    f"{lan['unexpectedError']} {e}\n\n"
                    f"```Error Details:\n"
                    f"Type: {exc_type.__name__}\n"
                    f"Message: {str(e)}\n"
                    f"File: {fname}\n"
                    f"Line Number: {line_no}\n"
                    f"Full Traceback: {traceback.format_exc()}```"
                )
                
                await interaction.followup.send(error_message, ephemeral=False)
                print(error_message)
                
                # Cleanup webhook if created
                if 'webhook' in locals() and webhook:
                    try:
                        await webhook.delete()
                    except Exception as cleanup_error:
                        print(f"Webhook cleanup error: {cleanup_error}")
        
        """@self.bot.tree.command(name="get_tokens_phpsessid", description="Set your Pixiv PHPSESSID token")
        async def get_tokens_phpsessid(interaction: discord.Interaction, token: str):
            self.PHPSESSID = token  # Store the token
            await interaction.response.send_message("PHPSESSID token set successfully!", ephemeral=True)"""
        
        class PixivImageManager:
            def __init__(self, base_path, keyword, image_urls, artwork_urls):
                self.base_path = base_path
                self.keyword = keyword
                self.pixiv_folder = os.path.join(base_path, "pixiv_Images", keyword)
                os.makedirs(self.pixiv_folder, exist_ok=True)
                
                # Store all URLs
                self.all_image_urls = image_urls
                self.all_artwork_urls = artwork_urls
                
                # Tracking variables
                self.downloaded_batches = {}  # Store batches {batch_start_index: [image_filenames]}
                self.current_batch_start = 0
                self.current_index = 0
                self.batch_size = 10
                self.preload_threshold = 3
                
                # Global image counter to ensure unique naming
                self.global_image_counter = 0
            
            async def download_batch(self, start_index):
                """
                Download a batch of images starting from the given index.
                
                Args:
                    start_index (int): Starting index for the batch
                
                Returns:
                    list: Successfully downloaded image filenames
                """
                # Prepare for this batch
                batch_image_urls = self.all_image_urls[start_index:start_index + self.batch_size]
                batch_artwork_urls = self.all_artwork_urls[start_index:start_index + self.batch_size]
                batch_images = []
                
                # Download images in the batch
                async with aiohttp.ClientSession() as session:
                    for idx, (image_url, artwork_url) in enumerate(zip(batch_image_urls, batch_artwork_urls), 1):
                        try:
                            # Increment global image counter for unique naming
                            self.global_image_counter += 1
                            
                            # Determine file extension
                            extension = image_url.split('.')[-1]
                            local_filename = os.path.join(self.pixiv_folder, f"a_{self.global_image_counter}.{extension}")
                            
                            # Download mechanism (similar to previous implementation)
                            headers = {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                                "Referer": f"https://www.pixiv.net/en/artworks/{artwork_url.split('/')[-1]}"
                            }

                            try:
                                async with session.get(image_url, headers=headers) as r:
                                    if r.status == 200:
                                        with open(local_filename, 'wb') as f:
                                            async for chunk in r.content.iter_chunked(1024):
                                                f.write(chunk)
                                
                                # If download successful, add to batch images
                                if os.path.exists(local_filename):
                                    batch_images.append(os.path.basename(local_filename))
                            
                            except aiohttp.ClientError as e:
                                print(f"Download failed for {local_filename}: {e}")
                            except Exception as e:
                                print(f"Error processing image {idx}: {e}")
                                
                                # Check if the image extension is '.jpg' and try downloading as '.png'
                                if extension.lower() == 'jpg':
                                    new_image_url = image_url.replace('.jpg', '.png')
                                    new_local_filename = os.path.join(self.pixiv_folder, f"a_{self.global_image_counter}.png")
                                    try:
                                        async with session.get(new_image_url, headers=headers) as r:
                                            if r.status == 200:
                                                with open(local_filename, 'wb') as f:
                                                    async for chunk in r.content.read_chunk():
                                                        f.write(chunk)
                                        
                                        # If second download attempt is successful, add to batch images
                                        if os.path.exists(new_local_filename):
                                            batch_images.append(os.path.basename(new_local_filename))
                                    except aiohttp.ClientError as e:
                                        print(f"Download failed for {local_filename}: {e}")
                                    except Exception as e:
                                        print(f"Error processing image {idx}: {e}")
                        
                        except Exception as e:
                            print(f"Error processing image {idx}: {e}")
                
                # Store this batch in downloaded batches
                self.downloaded_batches[start_index] = batch_images
                
                # Update current batch context
                self.current_batch_start = start_index
                self.current_index = 0
                
                return batch_images

            
            def get_next_batch(self):
                """
                Determine and download the next batch of images.
                
                Returns:
                    bool: True if more images are available, False otherwise
                """
                next_batch_start = self.current_batch_start + self.batch_size
                
                if next_batch_start < len(self.all_image_urls):
                    # Clean up previous batches if needed
                    self._cleanup_old_batches(next_batch_start)
                    
                    # Download next batch
                    self.download_batch(next_batch_start)
                    return True
                
                return False
            
            def get_previous_batch(self):
                """
                Load the previous batch of images.
                
                Returns:
                    bool: True if a previous batch exists, False otherwise
                """
                previous_batch_start = max(0, self.current_batch_start - self.batch_size)
                
                if previous_batch_start < self.current_batch_start:
                    # Clean up subsequent batches if needed
                    self._cleanup_subsequent_batches(previous_batch_start)
                    
                    # Download previous batch
                    self.download_batch(previous_batch_start)
                    return True
                
                return False
            
            def cleanup_old_images(self):
                """Remove old images when set becomes full"""
                for filename in os.listdir(self.pixiv_folder):
                    file_path = os.path.join(self.pixiv_folder, filename)
                    os.unlink(file_path)

            def _cleanup_old_batches(self, new_batch_start):
                """
                Remove batches before the new batch start.
                
                Args:
                    new_batch_start (int): Start index of the new batch
                """
                batches_to_remove = [
                    batch_start for batch_start in self.downloaded_batches 
                    if batch_start < new_batch_start
                ]
                
                for batch_start in batches_to_remove:
                    # Remove files for this batch
                    for filename in self.downloaded_batches[batch_start]:
                        file_path = os.path.join(self.pixiv_folder, filename)
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                    
                    # Remove batch from tracking
                    del self.downloaded_batches[batch_start]
            
            def _cleanup_subsequent_batches(self, previous_batch_start):
                """
                Remove batches after the previous batch start.
                
                Args:
                    previous_batch_start (int): Start index of the previous batch
                """
                batches_to_remove = [
                    batch_start for batch_start in self.downloaded_batches 
                    if batch_start > previous_batch_start
                ]
                
                for batch_start in batches_to_remove:
                    # Remove files for this batch
                    for filename in self.downloaded_batches[batch_start]:
                        file_path = os.path.join(self.pixiv_folder, filename)
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                    
                    # Remove batch from tracking
                    del self.downloaded_batches[batch_start]
            
            def next_image(self):
                """
                Move to the next image, potentially loading a new batch.
                
                Returns:
                    str or None: Path to the next image
                """
                # Check if we need to load a new batch
                if self.current_index >= len(self.downloaded_batches[self.current_batch_start]) - 1:
                    if not self.get_next_batch():
                        return None
                
                # Move to next image
                self.current_index += 1
                return self.get_current_image_path()
            
            def previous_image(self):
                """
                Move to the previous image, potentially loading a previous batch.
                
                Returns:
                    str or None: Path to the previous image
                """
                # If at the start of current batch, try to load previous batch
                if self.current_index == 0:
                    if self.get_previous_batch():
                        # Set to last image of the newly loaded batch
                        self.current_index = len(self.downloaded_batches[self.current_batch_start]) - 1
                        return self.get_current_image_path()
                    return None
                
                # Move to previous image
                self.current_index -= 1
                return self.get_current_image_path()
            
            def get_current_image_path(self):
                """
                Get the path of the current image.
                
                Returns:
                    str or None: Path to the current image
                """
                current_batch_images = self.downloaded_batches[self.current_batch_start]
                if 0 <= self.current_index < len(current_batch_images):
                    return os.path.join(self.pixiv_folder, current_batch_images[self.current_index])
                return None
            
            def get_current_artwork_url(self):
                """
                Get the artwork URL for the current image.
                
                Returns:
                    str or None: URL of the current artwork
                """
                current_global_index = self.current_batch_start + self.current_index
                if 0 <= current_global_index < len(self.all_artwork_urls):
                    return self.all_artwork_urls[current_global_index]
                return None

        class PixivImageNavigator(ui.View):
            def __init__(self, image_manager, timeout=1800):  # 30 minutes timeout
                super().__init__(timeout=timeout)
                self.image_manager = image_manager
            
            @ui.button(label="◀", style=ButtonStyle.primary)
            async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
                try:
                    # Add a blue circle reaction to the message
                    await interaction.response.defer()
                    await interaction.message.add_reaction("🔵")

                    # Process the previous image
                    prev_image = self.image_manager.previous_image()
                    if prev_image:
                        file = discord.File(prev_image, filename="image.png")
                        await interaction.message.edit(attachments=[file])

                    # Remove the blue circle reaction
                    await interaction.message.clear_reaction("🔵")
                except Exception as e:
                    # Log the error for debugging
                    print(f"Error in previous_button: {e}")

                    # Remove the blue circle reaction and add a red circle reaction
                    await interaction.message.clear_reaction("🔵")
                    await interaction.message.add_reaction("🔴")
            
            @ui.button(label="🌐", style=ButtonStyle.green)
            async def artwork_button(self, interaction: discord.Interaction, button: ui.Button):
                artwork_url = self.image_manager.get_current_artwork_url()
                if artwork_url:
                    await interaction.response.send_message(f"Artwork URL: {artwork_url}", ephemeral=True)
            
            @ui.button(label="▶", style=ButtonStyle.primary)
            async def next_button(self, interaction: discord.Interaction, button: ui.Button):
                try:
                    await interaction.response.defer()
                    # Add a blue circle reaction to the message
                    await interaction.message.add_reaction("🔵")

                    # Process the next image
                    next_image = self.image_manager.next_image()
                    if next_image:
                        file = discord.File(next_image, filename="image.png")
                        await interaction.message.edit(attachments=[file])

                    # Remove the blue circle reaction
                    await interaction.message.clear_reaction("🔵")
                except Exception as e:
                    # Log the error for debugging
                    print(f"Error in next_button: {e}")

                    # Remove the blue circle reaction and add a red circle reaction
                    await interaction.message.clear_reaction("🔵")
                    await interaction.message.add_reaction("🔴")
            
            async def on_timeout(self):
                # Clean up images on timeout
                self.image_manager.cleanup_old_images()

        @self.bot.tree.command(name="pixiv_search", description="Generates a Pixiv search URL")
        @app_commands.describe(
            keyword="The search keyword",
            order="Sorting order",
            sec_keyword_mode="Select or / add",
            search_type="Search type (illust or manga)",
            mode="Content mode",
            s_type="Search mode",
            search_filter_type="Filter type",
            page="Page number",
            start_date="Start date (YYYY-MM-DD)",
            end_date="End date (YYYY-MM-DD)",
            bookmarks="Minimum bookmarks"
        )
        @app_commands.choices(
            order=[
                app_commands.Choice(name="Newest", value="date_d"),
                app_commands.Choice(name="Oldest", value="date"),
                app_commands.Choice(name="Popular (All)", value="popular_d"),
                app_commands.Choice(name="Popular (Male)", value="popular_male_d"),
                app_commands.Choice(name="Popular (Female)", value="popular_female_d")
            ],
            search_type=[
                app_commands.Choice(name="Illustration", value="illust"),
                app_commands.Choice(name="Manga", value="manga")
            ],
            mode=[
                app_commands.Choice(name="All", value="all"),
                app_commands.Choice(name="Safe", value="safe"),
                app_commands.Choice(name="R-18", value="r18")
            ],
            s_type=[
                app_commands.Choice(name="Tag", value="s_tag"),
                app_commands.Choice(name="Tag (Full)", value="s_tag_full"),
                app_commands.Choice(name="Title & Caption", value="s_tc")
            ],
            search_filter_type=[
                app_commands.Choice(name="All", value="all"),
                app_commands.Choice(name="Illustration", value="illust"),
                #app_commands.Choice(name="Manga", value="manga"),
                #app_commands.Choice(name="Novel", value="novel"),
                #app_commands.Choice(name="User", value="user")
            ],
            sec_keyword_mode=[
                app_commands.Choice(name="Or", value = "or"),
                app_commands.Choice(name="And", value="and")
            ]
        )
        async def pixiv_search_command(
            interaction: discord.Interaction,
            keyword: str,
            secondary_keyword: str = None,
            order: str = "date_d",
            search_type: str = "illust",
            mode: str = "safe",
            s_type: str = "s_tag",
            search_filter_type: str = "all",
            page: int = 1,
            start_date: str = None,
            end_date: str = None,
            bookmarks: int = None,
            sec_keyword_mode: str = "or"
        ):
            await interaction.response.send_message("⚠️ This command is no longer supported. The Pixiv search functionality has been discontinued.", ephemeral=False)
            """await interaction.response.defer()

            cookies = {
                "PHPSESSID": ""  # !!! Remove this in production
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
                "Referer": "https://www.pixiv.net",
            }

            try:
                keyword = get_pixiv_autofill(keyword)

                # Process secondary keywords
                if secondary_keyword:
                    secondary_keywords = [get_pixiv_autofill(word.strip()) for word in secondary_keyword.split(",")]

                all_image_data = {}
                max_images = 55  # Set your desired maximum number of images
                max_pages = 500 # Set the maximum number of pages to fetch

                async with aiohttp.ClientSession() as session:
                    for current_page in range(1, max_pages + 1):
                        url = generate_pixiv_url(
                            keyword=keyword, order=order, mode=mode, page=current_page,
                            search_type=search_type, start_date=start_date,
                            end_date=end_date, bookmarks=bookmarks, s_type=s_type,
                            search_filter_type=search_filter_type
                        )

                        try:
                            async with session.get(url, headers=headers, cookies=cookies) as response:
                                response.raise_for_status()
                                data = await response.json()
                                print(f"Success,{current_page}\n")

                        except aiohttp.ClientError as e:
                            print(f"Error fetching page {current_page}: {e}")
                            # ... (handle error, potentially retry or break) ...
                        except Exception as e:
                            print(f"Unexpected error fetching page {current_page}: {e}")

                        if search_type is None:
                            search_term = "illust"
                        else:
                            search_term = "illustManga"

                        if data and data["body"][search_term]["data"]:
                            results = data["body"][search_term]["data"]
                            for result in results:
                                tags = result["tags"]

                                if secondary_keyword:
                                    if sec_keyword_mode == "or":
                                        if not any(keyword in tags for keyword in secondary_keywords):
                                            continue
                                    elif sec_keyword_mode == "and":
                                        if not all(keyword in tags for keyword in secondary_keywords):
                                            continue

                                illust_id = result['id']
                                create_date = result['createDate']
                                year, month, day = create_date.split('T')[0].split('-')
                                hour, minute, second = create_date.split('T')[1].split('+')[0].split(':')
                                extension = result['url'].split('.')[-1]
                                image_url = f"https://i.pximg.net/img-original/img/{year}/{month}/{day}/{hour}/{minute}/{second}/{illust_id}_p0.{extension}"
                                artwork_url = f"https://www.pixiv.net/en/artworks/{illust_id}"
                                all_image_data[image_url] = artwork_url
                                print()

                        # Break if we have enough images or no more results
                        if len(all_image_data) >= max_images or not results:
                            break

                    if all_image_data:
                        image_urls = list(all_image_data.keys())
                        artwork_urls = list(all_image_data.values())

                        channel_dir = self.get_channel_directory(interaction)
                        bot_id = "main_bot"
                        _ ,_, base_path = self.get_bot_paths(channel_dir, bot_id)
                        image_manager = PixivImageManager(base_path, keyword, image_urls, artwork_urls)

                        # Download first batch
                        await image_manager.download_batch(0)
                        print(len(image_urls))

                        # Create first image file
                        first_image_path = image_manager.get_current_image_path()
                        file = discord.File(first_image_path, filename="image.png")

                        # Create view with navigation
                        view = PixivImageNavigator(image_manager)

                        # Send initial message with image and navigation
                        await interaction.followup.send(file=file, view=view)
                        await interaction.followup.send("In alpha stages, several bugs to be fixed. You can help [here](<https://github.com/War004/Google-gemini-discord-bot>)",ephemeral=False)

                    else:
                        await interaction.followup.send("No images found.")
            except HTTPException as http_err:
                if http_err.code == 20009:
                    await interaction.followup.send(
                        "⚠️ The requested content contains explicit material and cannot be sent in this channel."
                    )
                else:
                    await interaction.followup.send(
                        f"⚠️ An unexpected error occurred: {http_err.text}"
                    )
                print(f"HTTPException: {http_err}")
            except CommandInvokeError as cmd_err:
                await interaction.followup.send(
                    "⚠️ There was an error executing the command. Please try again later."
                )
                print(f"CommandInvokeError: {cmd_err}")
            except Exception as e:
                await interaction.followup.send(
                    "⚠️ An unexpected error occurred. Please try again later."
                )
                print(f"Unexpected Error: {e}")
            finally:
                print("Request completed.")
                #Same images for different keywords
                #Not able to scroll after 10 Images
                #Interaction falied.
                #Error when expilt images
                """

        return {
                    "test": test_command,
                    #"check_token_usage": check_token_usage,
                    "info": info_command,
                    "add_webhook": add_webhook_command,
                    "remove_webhook": remove_webhook_command,
                    "remove_all_webhooks": remove_all_webhooks_command,
                    "reset_chat_history": reset_chat_history,
                    "add_v2_card_characters": add_v2_card_characters,
                    "remove_all_except": remove_all_except_command,
                    "edit_or_generate_image":edit_or_generate_image_command,
                    "change_model": change_model_command,
                    "pixiv_search": pixiv_search_command,
                    "clear_webhook_messages": clear_webhook_messages,
                    "set_language":set_language,
                    "clone_user":clone_user_command
                    #"get_tokens_phpsessid": get_tokens_phpsessid,
                    #"pixiv_image_search": embedpicture

                    # Add other commands to this dictionary
                }
