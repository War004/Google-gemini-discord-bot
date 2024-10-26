# utils.py
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
#from local_Version import custom_path


async def save_api_json(api_keys):
    with open("api_keys.json", "w") as f:
        json.dump(api_keys, f, indent=4)

async def load_api_keys():
    """Loads API keys from a JSON file.
    Returns an empty dictionary if the file doesn't exist or is corrupted.
    """
    if os.path.exists("api_keys.json"):
        with open("api_keys.json", "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error decoding API keys file. Creating a new one.")
                return {}  # Return empty dict if file is corrupted
    else:
        return {}

async def model_Loader(api_keys, channel_id):
    channel_data = api_keys.get(str(channel_id), {})
    model_name = channel_data.get('model_name')
    return model_name if model_name is not None else 'models/gemini-1.5-flash-exp-0827'


async def api_Checker(api_keys, channel_id):
    channel_id = str(channel_id)  # Ensure channel_id is a string
    
    if channel_id in api_keys:
        channel_data = api_keys[channel_id]
        
        api_key = channel_data.get('api_key')
        model_name = channel_data.get('model_name')
        
        if model_name is None:
            model_name = "models/gemini-1.5-flash-exp-0827"  # Set default if model_name is None
        
        if api_key:
            return api_key, model_name
        else:
            return None, model_name
    else:
        return False


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


def check_available_storage(attachments_dir):
    total, used, free = shutil.disk_usage(attachments_dir)
    return free
    """free_gb = free / (1024 ** 3) #GB
    return round(free_gb, 3)"""

def download_file(attachment_link: str, attachments_dir) -> tuple:
    """
    Downloads the file, determines its type, and saves it to the attachments directory.
    """
    try:
        # Check available storage
        free_storage = check_available_storage(attachments_dir)
        response = requests.head(attachment_link)
        download_size = int(response.headers.get('content-length', 0))
        
        if download_size > 0.6 * free_storage: # adjust according to need
            free_storage = free_storage / (1024 ** 3) #GB
            return None, round(free_gb, 3)
        
        # Parse the URL to get the file name without the extension
        parsed_link = urlparse(unquote(attachment_link))
        path = parsed_link.path
        original_filename = os.path.basename(path).split('?')[0]
        # Create a temporary filename with no extension within the attachments directory
        temp_filename_no_ext = os.path.join(attachments_dir, 'temp_file')
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
                return download_file(media_url, attachments_dir, channel)
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
def load_chat_history(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as file:
            pickle.dump([], file)
    with open(file_path, 'rb') as file:
        chat_history = pickle.load(file)
    return chat_history


# Function to save the chat history to a file
def save_chat_history(file_path, chat):
    with open(file_path, 'wb') as file:
        pickle.dump(chat.history, file)


def save_filetwo(file_path, url):
    if not os.path.exists(file_path):
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

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def check_expired_files(file_path, history):
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
    temporary = []

    for entry in data:
        upload_time = datetime.fromisoformat(entry['timestamp'])
        if current_time - upload_time > timedelta(hours=48):
            expired_files.append(entry)

    for dct in expired_files:
        temporary.append(dct['file_uri'])

    chat_history = history[:]  # Create a copy to avoid modifying the original list during iteration
    for link in temporary:
        chat_history = [entry for entry in chat_history if link not in str(entry)]

        data = [entry for entry in data if entry['file_uri'] != link]

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

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
    # await asyncio.sleep(0.0001)  # Adjust delay as needed
    await message.channel.send(
        f"<@{(message.author.id)}> ⚠️ The bot is currently processing another request. Please wait a moment.")


class GeminiErrorHandler:
    def __init__(self):
        # You can keep the error_messages dictionary for fallback 
        # in case the API doesn't provide a specific message
        self.error_messages = {
            400: "⚠️ Error 400: Invalid Argument. Please check your request format and parameters.",
            403: "⚠️ Error 403: Permission Denied. Check your API key and authentication.",
            404: "⚠️ Error 404: Not Found. The requested resource was not found.",
            429: "⚠️ Error 429: Too Many Requests. Please try again later.",
            500: "⚠️ Error 500: Internal Server Error. Please try again later or reduce the input context.",
            503: "⚠️ Error 503: Service Unavailable. Please try again later or switch to a different model.",
            504: "⚠️ Error 504: Deadline Exceeded. Please try again later or set a larger timeout."
        }

    async def handle_error(self, message: Message, error: GoogleAPIError, id_str: str):
        error_code = error.code if hasattr(error, "code") else 500
        
        # Try to extract the detailed error message from the Gemini API response
        try:
            # Assuming the error object has a 'message' or 'details' attribute
            # Adjust this based on the actual structure of the GoogleAPIError object
            error_message = error.message or error.details or str(error) 
        except AttributeError:
            error_message = self.error_messages.get(
                error_code,
                f"⚠️ An unexpected error occurred (code {error_code}). Please try again later."
            )

        if message:
            await send_message_main_bot(message, error_message)
        else:
            print(f"Error sending error message: No message object available.")

        print(f"Error: {error_message} (Details: {error})")


def load_webhook_system_instruction(webhook_id: str, channel_dir) -> str:
    json_file = os.path.join(channel_dir, "webhooks",
                             f"{webhook_id}_data.json")  # Assuming you store each webhook's data separately
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            webhook_data = json.load(f)
            return webhook_data.get("system_instructions", "")
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

error_handler = GeminiErrorHandler()

def text_gen_checker(model_Name, text_generation_config):
    #Some model doesn't support top_k = 0
    #this functions the values for these model and replace the top_k
    model_list = [
        "models/gemini-1.5-pro-002",
        "models/gemini-1.5-flash-002",
        "models/gemini-1.5-flash-8b",
        "models/gemini-1.5-flash-8b-001",
        "models/gemini-1.5-flash-8b-latest",
    ]
    if model_Name in model_list:
        text_generation_config['top_k'] = 40
    return text_generation_config

async def load_webhooks_from_disk(bot, base_path, webhooks):
    """Loads webhook data from disk and populates the webhooks dictionary."""

    for server_dir in os.listdir(base_path):
        server_path = os.path.join(base_path, server_dir)
        if not os.path.isdir(server_path):
            continue  # Skip if not a directory

        for channel_dir in os.listdir(server_path):
            channel_path = os.path.join(server_path, channel_dir)
            if not os.path.isdir(channel_path):
                continue  # Skip if not a directory

            webhooks_dir = os.path.join(channel_path, "webhooks")
            if not os.path.exists(webhooks_dir):
                continue  # Skip if webhooks directory doesn't exist

            for webhook_file in os.listdir(webhooks_dir):
                if not webhook_file.endswith("_data.json"):
                    continue  # Skip files that don't match the pattern

                webhook_data_path = os.path.join(webhooks_dir, webhook_file)
                try:
                    with open(webhook_data_path, "r") as f:
                        webhook_data = json.load(f)
                        webhook_id = int(webhook_data.get("webhook_user_id")) # Directly convert to int

                        # Fetch the webhook and store it in the dictionary
                        webhook = await bot.fetch_webhook(webhook_id)
                        webhooks[webhook.id] = webhook

                except (FileNotFoundError, json.JSONDecodeError):  # Handle file not found and JSON errors
                    print(f"Error loading webhook data from {webhook_data_path}. Skipping.")
                except discord.NotFound:
                    print(f"Webhook {webhook_id} not found, removing data file.")
                    os.remove(webhook_data_path)
                except discord.HTTPException as e:
                    print(f"HTTP Error fetching webhook {webhook_id}: {e}")
                except Exception as e:  # Catch other potential errors
                    print(f"Unexpected error loading webhook {webhook_id}: {e}")