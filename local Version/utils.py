# utils.py
# @title Functions
#Rembeer not to copy the timezone code
import discord
import io
import logging
from discord import app_commands,Message
import time
from random import choice, randint
import os
import requests
import asyncio
from pathlib import Path
import subprocess
from urllib.parse import urlparse, parse_qs, urlunparse, unquote
import re
import cv2
import shutil
import mimetypes
import magic
import json
import pickle
import concurrent.futures
from datetime import datetime, timedelta
import moviepy as mp
from bs4 import BeautifulSoup
#from google.api_core.exceptions import GoogleAPIError
from google import genai
from google.genai import types
from google.genai.types import Content
from typing import Optional
import aiofiles
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def is_youtube_link(url):
    """Checks if a URL is a YouTube video link (including Watch, Shorts, youtu.be)."""
    try:
        parsed_url = urlparse(url)
        host = parsed_url.netloc.lower()
        path = parsed_url.path

        # Check for youtu.be links (must have a path component for the ID)
        if host == 'youtu.be' and path and path != '/':
            return True

        # Check for youtube.com or m.youtube.com links
        if 'youtube.com' in host:
            # Check for /watch?v=... links
            if path == '/watch' and 'v' in parse_qs(parsed_url.query):
                return True
            # Check for /shorts/... links (must have something after /shorts/)
            if path.startswith('/shorts/') and len(path.split('/')) > 2 and path.split('/')[2]:
                return True

        return False
    except Exception:
        # Handle potential errors during parsing if URL is malformed
        return False


def extract_youtube_video_id(url):
    """Extracts the video ID from various YouTube URL formats."""
    try:
        parsed_url = urlparse(url)
        host = parsed_url.netloc.lower()
        path = parsed_url.path

        if 'youtu.be' in host:
            # For youtu.be URLs, the ID is the first part of the path
            video_id = path.split('/')[1] if path and len(path.split('/')) > 1 else None
            return video_id

        elif 'youtube.com' in host:
            # For youtube.com/watch URLs, get the 'v' query parameter
            if path == '/watch':
                query_params = parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            # For youtube.com/shorts/ URLs, the ID is the part after /shorts/
            elif path.startswith('/shorts/'):
                 # Path might be /shorts/ID or /shorts/ID/ (unlikely but handle)
                 parts = path.split('/')
                 if len(parts) > 2 and parts[2]:
                     return parts[2]
                 else:
                     return None
            else:
                return None # Other youtube.com paths are not video links we handle

        else:
            return None # Not a recognized YouTube video URL format
    except Exception:
        # Handle potential errors during parsing
        return None

def standardize_youtube_url(url):
    """Attempts to standardize a URL to the https://youtu.be/VIDEO_ID format."""
    if is_youtube_link(url):
        video_id = extract_youtube_video_id(url)
        if video_id:
            # Basic validation: YouTube IDs are typically 11 characters
            # consisting of letters, numbers, underscores, and hyphens.
            # Shorts IDs might have slightly different lengths/formats sometimes,
            # but this regex is a good general check. Adjust if needed.
            if re.match(r'^[a-zA-Z0-9_-]+$', video_id) and len(video_id) >= 10: # Relaxed length slightly
                 return f"https://youtu.be/{video_id}"
            else:
                print(f"Warning: Extracted potential YouTube ID '{video_id}' from '{url}' does not match expected format/length.")
                return None # Return None if ID format looks wrong
        else:
             print(f"Warning: Could not extract video ID from YouTube link: {url}")
             return None # Couldn't extract ID
    else:
        return None # Not a YouTube link


async def extract_response_text(response):
    """
    Extracts text and image data from the Gemini API response.

    Returns:
        (text_response, image_data): A tuple.
            - text_response:  A string containing the combined text, code,
                              code output, and source links (if any).
            - image_data:  A list of tuples, where each tuple contains
                              (mime_type, image_bytes), or None if no images are present.
    """
    if not response or not response.candidates: #added error handling, if for any reason we don't get the candiates. 
        return "No response from the model.", None

    first_candidate = response.candidates[0]
    parts = first_candidate.content.parts

    text_parts = []
    code_snippet = None
    code_output = None
    sources = []
    image_data = []  # List to store (mime_type, image_bytes) tuples

    for part in parts:
        if part.text:
            text_parts.append(part.text.strip())
        if part.executable_code:
            code_snippet = part.executable_code.code.strip()
        if part.code_execution_result:
            code_output = part.code_execution_result.output.strip()
        if part.inline_data and part.inline_data.mime_type.startswith('image/'):  # Check for image
            image_data.append((part.inline_data.mime_type, part.inline_data.data))

    combined_text = "\n".join(text_parts)

    # Source extraction (same as before, but factored into a helper function)
    sources = _extract_sources(first_candidate)
    formatted_sources = "\n".join([f"- [Source {i+1}](<{url}>)" for i, url in enumerate(sources)])

    response_sections = []
    if combined_text:
        response_sections.append(f"{combined_text}")
    if code_snippet:
        response_sections.append(f"Code:\n```python\n{code_snippet}```")
    if code_output:
        response_sections.append(f"Code Output: {code_output}")
    if formatted_sources:
        response_sections.append(f"\nSources\n{formatted_sources}")

    text_response = "\n\n".join(response_sections)

    return text_response, image_data if image_data else None  # Return image data or None

async def send_message_with_images_main_bot(message: Message, text_response: str, image_data: list):
    """Sends a message with text and multiple images via the main bot."""
    channel = message.channel

    # Send text response first (handling long messages as before)
    if text_response:  # Check if there's any text to send
        if len(text_response) <= 2000:
            await channel.send(text_response)
        else:
            chunks = re.findall(r".{1,2000}(?:\s|$)", text_response, re.DOTALL)
            for chunk in chunks:
                chunk = chunk.strip()
                if chunk:
                    await channel.send(chunk)

    # Send each image as a separate file
    for mime_type, image_bytes in image_data:
        try:
            filename = f"gemini_image.{mime_type.split('/')[-1]}"  # e.g., gemini_image.png
            image_file = discord.File(io.BytesIO(image_bytes), filename=filename)
            await channel.send(file=image_file)
        except Exception as e:
            error_message = f"Error sending image: {e}"
            await channel.send(error_message) #send error message if it couldn't.

def _extract_sources(candidate):
    """Helper function to extract sources (reduces duplication)."""
    sources = []
    if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
        grounding_metadata = candidate.grounding_metadata
        if hasattr(grounding_metadata, 'grounding_supports') and grounding_metadata.grounding_supports:
            for grounding_support in grounding_metadata.grounding_supports:
                if hasattr(grounding_support, 'grounding_chunk_indices') and grounding_support.grounding_chunk_indices:
                    for chunk_index in grounding_support.grounding_chunk_indices:
                        if (hasattr(grounding_metadata, 'grounding_chunks') and
                                grounding_metadata.grounding_chunks and
                                chunk_index < len(grounding_metadata.grounding_chunks)):
                            grounding_chunk = grounding_metadata.grounding_chunks[chunk_index]
                            if hasattr(grounding_chunk, 'web') and grounding_chunk.web:
                                if hasattr(grounding_chunk.web, 'uri') and grounding_chunk.web.uri:
                                    sources.append(grounding_chunk.web.uri)
    return list(set(sources))  # Remove duplicates

async def save_api_json(api_keys_data: dict, filepath: str = "api_keys.json"):
    """
    Asynchronously saves the api_keys dictionary to a JSON file.
    """
    try:
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(api_keys_data, indent=4))
        # print(f"Successfully saved API keys to {filepath}") # Optional: for debugging
    except IOError as e:
        print(f"An IOError occurred while saving API keys to {filepath}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving API keys to {filepath}: {e}")

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
    return model_name if model_name is not None else 'models/gemini-2.0-flash-exp'


async def api_Checker(api_keys, channel_id):
    channel_id = str(channel_id)

    if channel_id in api_keys:
        channel_data = api_keys[channel_id]

        api_key = channel_data.get('api_key')
        model_name = channel_data.get('model_name')
        language = channel_data.get('language') # Get language, might be None

        # Explicitly check for None and default to 'en' if it is None
        if language is None:
            language = 'en'

        if model_name is None:
            model_name = "models/gemini-2.0-flash-exp"

        if api_key:
            return api_key, model_name, language
        else:
            # Even if API key is None, return the determined language
            return None, model_name, language
    else:
        # Channel not found, default language is 'en'
        return False, None, 'en'


def create_chat_with_proper_history(client, history_dicts, model_name,blockValue,system_instruction):
    """
    Convert dictionary-based history to Content objects for Gemini API
    """
    # Convert each dictionary in history to a Content object
    proper_history = []
    for msg in history_dicts:
        # Create a Content object with the appropriate role and parts
        if isinstance(msg, dict):
            # If it's a dict, convert it to a Content object
            role = msg.get('role', 'user')  # Default to 'user' if not specified
            parts = msg.get('parts', [msg.get('text', '')])
            proper_history.append(Content(role=role, parts=parts))
        else:
            # If it's already a Content object, just add it
            proper_history.append(msg)
    
    # Create the chat with proper Content objects
    return client.aio.chats.create(
        model=model_name,
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
                        ],
        history=proper_history
    ))
    
def upload_to_gemini(path,client):  # Remove mime_type argument
    """Uploads the given file to Gemini."""
    file = client.files.upload(path=path)  # Remove mime_type keyword
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    file_uri = file.uri  # Get the URI from the media_file object
    mime_type = file.mime_type  # Get the mime_type from the media_file object
    media_part = types.Part.from_uri(file_uri=file_uri, mime_type=mime_type)
    return media_part

import asyncio

async def wait_for_file_activation(name: str, client) -> bool:
    """
    Waits for a file to become active and then returns file information.

    Args:
        name: The name of the file to wait for.

    Returns:
        File information using client.files.get or None if there was an error.
    """

    while True:
        try:
            file = await client.aio.files.get(name=name)
            if file.state == "ACTIVE":
                print(f"File '{name}' is now active.")
                return True
            elif file.state == "PROCESSING":
                print(f"File '{name}' is still processing. Waiting 5 seconds...")
                await asyncio.sleep(5)  # Non-blocking sleep
            else:
                print(f"Error: Unexpected file state for '{name}': {file.state}")
                return None  # Or raise an exception if preferred
        except Exception as e:
            print(f"Error while checking file '{name}': {e}")
            return None

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
            return None, round(free_storage, 3)
        
        # Parse the URL to get the file name without the extension
        parsed_link = urlparse(unquote(attachment_link))
        path = parsed_link.path
        original_filename = os.path.basename(path).split('?')[0]
        
        # Create a temporary filename with no extension
        temp_filename_no_ext = os.path.join(attachments_dir, 'temp_file')
        
        # Delete the temp file if it already exists
        if os.path.exists(temp_filename_no_ext):
            os.remove(temp_filename_no_ext)
            print(f"Deleted existing temporary file: {temp_filename_no_ext}")
        
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
                return download_file(media_url, attachments_dir)
            else:
                raise ValueError("Unable to extract media URL from Tenor HTML")
                
        # Check if destination file exists and delete it first
        final_filename = f'{temp_filename_no_ext}{extension}'
        if os.path.exists(final_filename):
            os.remove(final_filename)
            print(f"Deleted existing destination file: {final_filename}")
            
        os.rename(temp_filename_no_ext, final_filename)
        print(f"File renamed to: {final_filename} with MIME type: {mime_type}")
        
        return mime_type, final_filename
    except requests.RequestException as e:
        print(f"Failed to download file. Error: {e}")
        return None, None
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def extract_audio(video_path, output_path):
    """
    Asynchronously extracts audio from a video file.

    Args:
        video_path: Path to the input video file.
        output_path: Path to save the extracted audio file (e.g., .mp3, .wav).
    """
    try:
        loop = asyncio.get_running_loop()
        clip = mp.VideoFileClip(video_path)
        audio = clip.audio

        def _extract():
            # asyncio should be accessible here now 
            audio.write_audiofile(output_path)

        await loop.run_in_executor(thread_pool, _extract)  # Use your existing thread pool
        print(f"Audio extracted to: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

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
async def load_chat_history(file_path: str):
    """
    Asynchronously loads chat history from a pickle file.
    Creates an empty history file if it doesn't exist.
    """
    loop = asyncio.get_event_loop() # Get the current event loop

    try:
        # Asynchronously check if file exists
        file_exists = await loop.run_in_executor(None, os.path.exists, file_path)

        if not file_exists:
            # Asynchronously create and write empty list if file doesn't exist
            async with aiofiles.open(file_path, 'wb') as f_new:
                await f_new.write(pickle.dumps([]))
            return [] # Return empty list immediately

        # Asynchronously open and read the file
        async with aiofiles.open(file_path, 'rb') as f_existing:
            content_bytes = await f_existing.read()
            if not content_bytes: # Handle empty file case
                return []
            chat_history = pickle.loads(content_bytes)
        return chat_history
    except FileNotFoundError: # Should be caught by os.path.exists, but good to have
        print(f"File not found at {file_path}, returning empty history.")
        return []
    except pickle.UnpicklingError as e:
        print(f"Error unpickling data from {file_path}: {e}. Returning empty history.")
        # Optionally, you might want to delete or rename the corrupted file here
        return []
    except Exception as e:
        print(f"An unexpected error occurred loading chat history from {file_path}: {e}")
        return [] # Or re-raise the exception if that's preferred


# Function to save the chat history to a file
def save_chat_history(file_path, chat):
    with open(file_path, 'wb') as file:
        #pickle.dump(chat._curated_history, file)
        pickle.dump(chat._curated_history, file)

def mess_Index(chat_history):
    return (len(chat_history))

def save_filetwo(file_path, url, message_index):
    #print("In save_filetwo")
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
        'timestamp': datetime.now().isoformat(),
        'message_index': message_index
    }
    data.append(new_data)

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def modify_history(history, indices_to_keep):
    """
    Creates a new chat history containing only the entries at the specified indices.

    Args:
        history: The original chat history list.
        indices_to_keep: A list of integer indices to keep from the history.

    Returns:
        A new list representing the filtered chat history.
    """
    new_history = []
    for index in indices_to_keep:
        if 0 <= index < len(history):  # Ensure index is within bounds
            new_history.append(history[index])
    return new_history

async def check_expired_files(file_path, history, chat_history_path):
    """
    Checks for expired files (older than 40 hours) in a JSON file and conditionally
    removes corresponding entries from the chat history and JSON file based on
    a re-checking process.

    Args:
        file_path: Path to the JSON file storing file metadata.
        history: The chat history list.
        chat_history_path: Path to pickle file storing the chat history

    Returns:
        A new list representing the updated chat history (or the original
        if no changes were needed).
    """

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump([], file)
        return list(history)

    with open(file_path, 'r') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            return list(history)

    current_time = datetime.utcnow()
    has_expired_files = False

    for entry in data:
        upload_time = datetime.fromisoformat(entry['timestamp'])
        if current_time - upload_time > timedelta(hours=40): #changed to 40 hours because the files were still expiring before 48 hours
            has_expired_files = True
            break

    if not has_expired_files:
        return list(history)  # Do nothing if no expired files

    # --- Expired files found, continue processing ---

    expired_indices = set()
    updated_data = []

    for entry in data:
        upload_time = datetime.fromisoformat(entry['timestamp'])
        if current_time - upload_time > timedelta(hours=48):
            if 'message_index' in entry:
                expired_indices.add(entry['message_index'])
        else:
            updated_data.append(entry)

    new_history = [item for i, item in enumerate(history) if i not in expired_indices]

    # Save the new_history (first pass)
    with open(chat_history_path, 'wb') as file:
        pickle.dump(new_history, file)

    # Re-checking layer
    reCheckingHistory = await load_chat_history(chat_history_path)
    rechecked_history = await filter_history(reCheckingHistory)

    # Compare new_history and rechecked_history
    if new_history == rechecked_history:
        # If they are the same, remove JSON entries and return new_history
        with open(file_path, 'w') as file:
            json.dump(updated_data, file, indent=4)
        return new_history
    else:
        # If they are different, save rechecked_history, remove JSON entries, and return rechecked_history
        with open(chat_history_path, 'wb') as file:
            pickle.dump(rechecked_history, file)
        with open(file_path, 'w') as file:
            json.dump(updated_data, file, indent=4)
        return rechecked_history

# Example usage (assuming you have 'file_data.json' and a 'chat_history' list):
# file_path = 'file_data.json'
# chat_history = ["message 0", "message 1", "message 2", "message 3", "message 4", "message 5"]
# updated_history = check_expired_files(file_path, chat_history)
# print(updated_history)

async def filter_history(history):
    search_patterns = [
        "https://generativelanguage.googleapis.com/v1beta/files/"
    ]
    
    filtered_history = []
    removed_indices = []
    
    for index, entry in enumerate(history):
        entry_str = str(entry).lower()  # Convert to string and lowercase for case-insensitive search
        should_keep = True
        
        for pattern in search_patterns:
            if pattern.lower() in entry_str:
                should_keep = False
                print(f'Found match "{pattern}" at index {index}')
                print(f'Removed message: {entry}')
                removed_indices.append(index)
                break
                
        if should_keep:
            filtered_history.append(entry)
        await asyncio.sleep(0)  # Yield control to the event loop
    
    if removed_indices:
        print(f'Messages removed at indices: {removed_indices}')
    else:
        print('No matches found')
        
    return filtered_history

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

"""
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
        """


def load_webhook_system_instruction(webhook_id: str, channel_dir) -> str:
    json_file = os.path.join(channel_dir, "webhooks",
                             f"{webhook_id}_data.json")  # Assuming you store each webhook's data separately
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            webhook_data = json.load(f)
            return webhook_data.get("system_instructions", "")
    return "You are a helpful assistant."

async def load_webhook_system_instruction_tokens(webhook_id: str, channel_dir,client: genai.Client) -> int:
    json_file = os.path.join(channel_dir, "webhooks", f"{webhook_id}_data.json")

    file_exists_and_readable = False
    try:
        # Check if file exists and is accessible by trying to get its status
        await aiofiles.os.stat(json_file)
        file_exists_and_readable = True
    except FileNotFoundError:
        # File doesn't exist, defaults will be used
        pass
    except Exception:
        # Other error (e.g., permission denied), defaults will be used
        # You might want to log this error for debugging
        pass

    if file_exists_and_readable:
        try:
            async with aiofiles.open(json_file, mode="r", encoding="utf-8") as f:
                content = await f.read()
                webhook_data = json.loads(content) # Use json.loads for string content
                
                # New logic for total_tokens:
                # If the "total_tokens" key exists in the JSON, return it.
                if "total_tokens" in webhook_data:
                    total_tokens = webhook_data.get("total_tokens", total_tokens)
                    return total_tokens
                else:
                    system_instructions = webhook_data.get("system_instructions", system_instructions)

                    if system_instruction:
                        token_count_response = await client.aio.models.count_tokens(
                            model='models/gemini-2.5-flash-preview-05-20',
                            contents=system_instructions
                        )
                        webhook_data["total_tokens"] = token_count_response.total_tokens
                        
                        try:
                            with open(json_file_path, "w") as f:
                                json.dump(webhook_data, f, indent=4)
                            print(f"Successfully updated and saved webhook data for {webhook_id} to {json_file_path}")
                            return webhook_data
                        except IOError as e:
                            print(f"Error writing JSON file {json_file_path}: {e}")
                            return None

                        return token_count_response.total_tokens
                    
                    else:
                        return -1
                    
        except json.JSONDecodeError:
            # Handle cases where the JSON is malformed.
            # system_instructions_to_return and total_tokens_to_return will retain their initial defaults.
            # You might want to log this error
            pass
        except Exception:
            # Handle other potential errors during file reading or JSON processing.
            # Defaults will be used. You might want to log this error.
            pass
    return 7829


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

    if response is None:
        response = "No response from the API."
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

#error_handler = GeminiErrorHandler()

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

async def load_webhooks_from_disk(bot, base_path, webhooks_dict_ref): # Pass webhooks dict by reference
    """
    Loads webhook data from disk and populates the webhooks dictionary. Runs as a background task.
    `webhooks_dict_ref` is the dictionary to update.
    """
    logging.info("BACKGROUND_TASK: load_webhooks_from_disk started.")
    loaded_count = 0
    error_count = 0

    try:
        os.makedirs(base_path, exist_ok=True)
    except OSError as e:
        logging.error(f"BACKGROUND_TASK: Could not create base path '{base_path}': {e}. Cannot load webhooks from disk.")
        return
    
    if not os.path.isdir(base_path):
        logging.warning(f"BACKGROUND_TASK: load_webhooks_from_disk - Base path '{base_path}' is a file, not a directory. Cannot load webhooks from disk.")
        return

    for server_dir in os.listdir(base_path):
        server_path = os.path.join(base_path, server_dir)
        if not os.path.isdir(server_path):
            continue

        for channel_dir_name in os.listdir(server_path): # Renamed to avoid conflict
            channel_path = os.path.join(server_path, channel_dir_name)
            if not os.path.isdir(channel_path):
                continue

            webhooks_json_dir = os.path.join(channel_path, "webhooks") # Corrected variable name
            if not os.path.exists(webhooks_json_dir) or not os.path.isdir(webhooks_json_dir):
                continue

            for webhook_file in os.listdir(webhooks_json_dir):
                if not webhook_file.endswith("_data.json"):
                    continue

                webhook_data_path = os.path.join(webhooks_json_dir, webhook_file)
                webhook_id_from_file = None
                try:
                    with open(webhook_data_path, "r", encoding="utf-8") as f:
                        webhook_data = json.load(f)
                        webhook_id_from_file = int(webhook_data.get("webhook_user_id"))

                    if webhook_id_from_file:
                        # Check if already fetched to avoid re-fetching if this task runs multiple times or overlaps
                        if webhook_id_from_file not in webhooks_dict_ref:
                            webhook_obj = await bot.fetch_webhook(webhook_id_from_file) # This is a network call
                            webhooks_dict_ref[webhook_obj.id] = webhook_obj # Update the passed dictionary
                            loaded_count += 1
                        # else:
                        #     logging.debug(f"BACKGROUND_TASK: Webhook {webhook_id_from_file} already in memory.")
                    else:
                        logging.warning(f"BACKGROUND_TASK: Missing 'webhook_user_id' in {webhook_data_path}")
                        error_count +=1

                except FileNotFoundError:
                    logging.warning(f"BACKGROUND_TASK: Webhook data file not found (should not happen if os.listdir worked): {webhook_data_path}")
                    error_count +=1
                except (json.JSONDecodeError, ValueError) as e: # ValueError for int conversion
                    logging.error(f"BACKGROUND_TASK: Error processing webhook data file {webhook_data_path}: {e}")
                    error_count +=1
                except discord.NotFound:
                    logging.warning(f"BACKGROUND_TASK: Webhook {webhook_id_from_file} (from {webhook_data_path}) not found on Discord. Removing data file.")
                    try:
                        os.remove(webhook_data_path)
                    except OSError as e_os:
                        logging.error(f"BACKGROUND_TASK: Failed to remove stale webhook data file {webhook_data_path}: {e_os}")
                    error_count +=1
                except discord.HTTPException as e:
                    logging.error(f"BACKGROUND_TASK: HTTP Error fetching webhook {webhook_id_from_file} (from {webhook_data_path}): {e}", exc_info=True)
                    error_count +=1
                except Exception as e:
                    logging.error(f"BACKGROUND_TASK: Unexpected error loading webhook {webhook_id_from_file} (from {webhook_data_path}): {e}", exc_info=True)
                    error_count +=1
    logging.info(f"BACKGROUND_TASK: load_webhooks_from_disk finished. Loaded {loaded_count} new webhooks. Encountered {error_count} errors.")
