# @title Functions
#Rembeer not to copy the timezone code
import discord
from discord import app_commands,Message
import time
from random import choice, randint
import os
import requests
from urllib.parse import urlparse, unquote
import re
import cv2
import shutil
import mimetypes
import magic
import json
import pickle
from datetime import datetime, timedelta
import moviepy.editor as mp
from bs4 import BeautifulSoup
from google.api_core.exceptions import GoogleAPIError
import google.generativeai as genai

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")
    print()

def download_file(attachment_link: str, user_id: str) -> tuple:
    """
    Downloads the file, determines its type, and renames it with the correct extension.
    """
    try:
        # Parse the URL to get the file name without the extension
        parsed_link = urlparse(unquote(attachment_link))
        path = parsed_link.path
        original_filename = os.path.basename(path).split('?')[0]

        # Create a temporary filename with the user_id as prefix and no extension
        temp_filename = f'file_{user_id}'
        temp_filename_no_ext = temp_filename.rsplit('.', 1)[0]

        # Download the file
        response = requests.get(attachment_link)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Save the file without an extension
        with open(temp_filename_no_ext, 'wb') as f:
            f.write(response.content)

        print(f"File downloaded successfully: {temp_filename_no_ext}")

        # Determine the file type and the correct extension
        mime_type = determine_file_type(temp_filename_no_ext)
        extension = mimetypes.guess_extension(mime_type) or '.bin'  # Default to .bin if unknown

        # Check if the downloaded file is actually a GIF
        if mime_type == 'text/html' and 'tenor.com' in parsed_link.netloc:
            media_url = extract_media_url_from_html(temp_filename_no_ext)
            if media_url:
                os.remove(temp_filename_no_ext)
                return download_file(media_url, user_id)
            else:
                raise ValueError("Unable to extract media URL from Tenor HTML")

        # Rename the file with the correct extension
        final_filename = f'{temp_filename_no_ext}{extension}'
        os.rename(temp_filename_no_ext, final_filename)
        print(f"File renamed to: {final_filename} with MIME type: {mime_type}")

        return mime_type, final_filename
    except requests.RequestException as e:
        print(f"Failed to download file. Error: {e}")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return

def determine_file_type(filepath: str) -> str:
    """
    Determines the MIME type of a file by reading its contents.
    """
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(filepath)
        return mime_type
    except Exception as e:
        print(f"Could not determine file type. Error: {e}")
        return 'application/octet-stream'

# Function to load chat history from a file
def load_chat_history(user_id, custom_file_path, bot_id):
    full_path = os.path.join(custom_file_path, f'{bot_id}_{user_id}_chat_history.pkl')
    os.makedirs(custom_file_path, exist_ok=True)

    if not os.path.exists(full_path):
        with open(full_path, 'wb') as file:
            pickle.dump([], file)

    with open(full_path, 'rb') as file:
        chat_history = pickle.load(file)

    return chat_history

# Function to save the chat history from a file
def save_chat_history(user_id, chat, custom_file_path, bot_id):
    full_path = os.path.join(custom_file_path, f'{bot_id}_{user_id}_chat_history.pkl')  # Use os.path.join
    with open(full_path, 'wb') as file:
        pickle.dump(chat.history, file)

def save_filetwo(user_id, time_file_path, url, bot_id):
    file_name = f'{bot_id}_{user_id}_files_metadata.json'
    file_path = os.path.join(time_file_path, file_name)   

    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        with open(file_path, 'w') as file:
            json.dump([], file)

    with open(file_path, 'r') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            data = []

    new_data = {
        'file_uri': url,
        'timestamp': datetime.now().isoformat()
    }
    data.append(new_data)
    print(file_path)

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
        print("Successful saved the file url and upload time")

def check_expired_files(user_id, time_file_path, history, bot_id):
    tempoery = []
    chat_history = history
    file_path = os.path.join(time_file_path, f'{bot_id}_{user_id}_files_metadata.json')

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump([], file)
        return history

    with open(file_path, 'r') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            data = []

    current_time = datetime.utcnow()
    expired_files = []

    for entry in data:
        upload_time = datetime.fromisoformat(entry['timestamp'])
        if current_time - upload_time > timedelta(hours=48):
            expired_files.append(entry)

        for dct in expired_files:
            tempoery.append(dct['file_uri'])

        for link in tempoery:
            target_word = (f'{link}')
            chat_history = [entry for entry in chat_history if target_word not in str(entry)]
            print(f'Successfully removed: {target_word}')

            data = [entry for entry in data if entry['file_uri'] != target_word]

            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
                print("Successfully updated the file_metadata.json")

    return chat_history

def extract_media_url_from_html(html_file_path):
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    media_url = None
    for meta in soup.find_all('meta'):
        if meta.get('name') == 'twitter:player:stream':
            media_url = meta.get('content')
            break

    return media_url

async def send_processing_notice(message: Message) -> None:  # Define the function
    """Sends the "Processing message" notice after a short delay."""
    #await asyncio.sleep(0.0001)  # Adjust delay as needed
    await message.channel.send(f"<@{(message.author.id)}> ⚠️ The bot is currently processing another request. Please wait a moment.")

class GeminiErrorHandler:
    def __init__(self):
        self.error_messages = {
            400: "⚠️ Error 400: Invalid Argument. Please check your request format and parameters. Please if eariler you were using the model 'gemini 1.0 pro' and then switched to any model for gemini 1.5 it will cause error.",
            403: "⚠️ Error 403: Permission Denied. Check your API key and authentication.",
            404: "⚠️ Error 404: Not Found. The requested resource was not found.",
            429: "⚠️ Error 429: Too Many Requests. Please try again later.",
            500: "⚠️ Error 500: Internal Server Error. Please try again later or reduce the input context.",
            503: "⚠️ Error 503: Service Unavailable. Please try again later or switch to a different model.",
            504: "⚠️ Error 504: Deadline Exceeded. Please try again later or set a larger timeout."
        }

    async def handle_error(self, message: Message, error: GoogleAPIError, id_str: str):
        error_code = error.code if hasattr(error, "code") else 500
        error_message = self.error_messages.get(
            error_code,
            f"⚠️ An unexpected error occurred (code {error_code}). Please try again later."
        )

        if message:  # Check if the message object is available
            await send_message_main_bot(message, error_message)  # Use the main bot function
        else:
            print(f"Error sending error message: No message object available.")  # Log the error

        print(f"Error: {error_message} (Details: {error})")

def load_webhook_system_instruction(webhook_id: str, webhooks_path=None) -> str:
    json_file = os.path.join(webhooks_path, "webhooks_data.json")
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            webhooks_dict = json.load(f)

        webhook_data = webhooks_dict.get(webhook_id)
        if webhook_data:
            return webhook_data.get("system_instructions", "")

    # If we can't find the specific webhook instruction, return a default
    return "You are a helpful assistant."

async def send_message_main_bot(message: Message, response: str) -> None:
    """Sends a message to the channel where the original message was received."""

    print("Sending message via main bot...")
    destination = message.channel

    if len(response) <= 2000:
        await destination.send(response)
    else:
        chunks = re.findall(r".{1,2000}(?:\s|$)", response, re.DOTALL)
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                await destination.send(chunk)


async def send_message_webhook(webhook: discord.Webhook, response: str) -> None:
    """Sends a message using the specified webhook."""

    print("Sending message via webhook...")
    destination = webhook

    if len(response) <= 2000:
        await destination.send(response)
    else:
        chunks = re.findall(r".{1,2000}(?:\s|$)", response, re.DOTALL)
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                await destination.send(chunk)

# Create an instance of the error handler