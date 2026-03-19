"""
Centralized media processing for Discord → Gemini.

Handles:
- Discord attachments (images, GIFs, videos, audio) — streamed from memory, no local save
- URLs in messages (images/GIFs/videos only, no HTML pages)
- YouTube links — passed directly as Part.from_uri(), no upload needed
"""

import io
import re
import asyncio
import logging
import aiohttp
from urllib.parse import urlparse, parse_qs

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Supported MIME type prefixes for URL downloads (reject HTML, etc.)
SUPPORTED_MEDIA_PREFIXES = ("image/", "video/", "audio/")

# Max file size for URL downloads (50 MB)
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024


def is_youtube_link(url: str) -> bool:
    """Checks if a URL is a YouTube video link."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path

        if host == "youtu.be" and path and path != "/":
            return True

        if "youtube.com" in host:
            if path == "/watch" and "v" in parse_qs(parsed.query):
                return True
            if path.startswith("/shorts/") and len(path.split("/")) > 2 and path.split("/")[2]:
                return True

        return False
    except Exception:
        return False


def standardize_youtube_url(url: str) -> str | None:
    """Converts any YouTube URL format to https://youtu.be/{VIDEO_ID}."""
    if not is_youtube_link(url):
        return None

    video_id = _extract_youtube_video_id(url)
    if video_id and re.match(r"^[a-zA-Z0-9_-]+$", video_id) and len(video_id) >= 10:
        return f"https://youtu.be/{video_id}"

    logger.warning("Could not extract valid YouTube video ID from: %s", url)
    return None


def _extract_youtube_video_id(url: str) -> str | None:
    """Extracts the video ID from various YouTube URL formats."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path

        if "youtu.be" in host:
            parts = path.split("/")
            return parts[1] if len(parts) > 1 else None

        if "youtube.com" in host:
            if path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            if path.startswith("/shorts/"):
                parts = path.split("/")
                return parts[2] if len(parts) > 2 and parts[2] else None

        return None
    except Exception:
        return None


def _youtube_to_part(youtube_url: str) -> types.Part:
    """Creates a Gemini Part from a YouTube URL (no upload needed)."""
    return types.Part.from_uri(file_uri=youtube_url, mime_type="video/*")


async def _upload_bytes_to_gemini(
    data: bytes,
    mime_type: str,
    display_name: str,
    client: genai.Client,
) -> types.Part:
    """
    Uploads raw bytes to the Gemini Files API and waits for activation.
    Returns a Part ready to be sent in a chat message.
    """
    logger.info("Uploading '%s' (%s, %d bytes) to Gemini Files API...", display_name, mime_type, len(data))

    file_obj = await client.aio.files.upload(
        file=io.BytesIO(data),
        config=types.UploadFileConfig(
            mime_type=mime_type,
            display_name=display_name,
        ),
    )

    logger.info("Upload complete: %s (state: %s)", file_obj.name, file_obj.state)

    # Wait for file to become ACTIVE
    await _wait_for_activation(file_obj.name, client)

    return types.Part.from_uri(file_uri=file_obj.uri, mime_type=file_obj.mime_type), file_obj.uri


async def _wait_for_activation(file_name: str, client: genai.Client, timeout: int = 120) -> None:
    """Polls until the uploaded file state is ACTIVE or times out."""
    elapsed = 0
    interval = 3

    while elapsed < timeout:
        file_info = await client.aio.files.get(name=file_name)

        if file_info.state == "ACTIVE":
            logger.info("File '%s' is now ACTIVE.", file_name)
            return

        if file_info.state != "PROCESSING":
            raise RuntimeError(f"File '{file_name}' entered unexpected state: {file_info.state}")

        logger.debug("File '%s' still PROCESSING, waiting %ds...", file_name, interval)
        await asyncio.sleep(interval)
        elapsed += interval

    raise TimeoutError(f"File '{file_name}' did not become ACTIVE within {timeout}s")


async def _download_url(url: str) -> tuple[bytes, str] | None:
    """
    Downloads a URL in-memory. Returns (data, mime_type) or None if:
    - Content-Type is not a supported media type (rejects HTML, JSON, etc.)
    - File is too large
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    logger.warning("URL download failed with status %d: %s", resp.status, url)
                    return None

                content_type = resp.content_type or ""

                # Reject non-media content types (HTML pages, JSON, etc.)
                if not any(content_type.startswith(prefix) for prefix in SUPPORTED_MEDIA_PREFIXES):
                    logger.info("Skipping URL — unsupported Content-Type '%s': %s", content_type, url)
                    return None

                # Check content length if available
                content_length = resp.content_length
                if content_length and content_length > MAX_DOWNLOAD_SIZE:
                    logger.warning("URL too large (%d bytes): %s", content_length, url)
                    return None

                data = await resp.read()

                if len(data) > MAX_DOWNLOAD_SIZE:
                    logger.warning("Downloaded data too large (%d bytes): %s", len(data), url)
                    return None

                logger.info("Downloaded %d bytes (%s) from: %s", len(data), content_type, url)
                return data, content_type

    except Exception as e:
        logger.error("Failed to download URL '%s': %s", url, e)
        return None


def _extract_urls(text: str) -> list[str]:
    """Extracts all URLs from a message text."""
    return re.findall(r"(https?://[^\s]+)", text)


class MediaProcessor:
    """
    Centralized media processing for the bot.

    Usage:
        processor = MediaProcessor()
        parts, file_uris = await processor.process(message, client)
        # parts: list of types.Part to include in the Gemini message
        # file_uris: list of uploaded file URIs (for tracking expiry)
    """

    async def process(
        self,
        message,
        client: genai.Client,
    ) -> tuple[list[types.Part], list[str]]:
        """
        Processes all media in a Discord message.

        Returns:
            (media_parts, file_uris):
                - media_parts: list of types.Part for Gemini
                - file_uris: list of uploaded file URIs (for MediaTracker)
                  YouTube links return an empty file_uris since they don't expire.
        """
        media_parts: list[types.Part] = []
        file_uris: list[str] = []

        # 1. Process Discord attachments (direct uploads)
        if message.attachments:
            for attachment in message.attachments:
                try:
                    part, uri = await self._process_attachment(attachment, client)
                    media_parts.append(part)
                    file_uris.append(uri)
                    logger.info("Processed attachment: %s", attachment.filename)
                except Exception as e:
                    logger.error("Failed to process attachment '%s': %s", attachment.filename, e)

        # 2. Check for URLs in the message text
        urls = _extract_urls(message.content)
        for url in urls:
            try:
                # Check YouTube first
                yt_url = standardize_youtube_url(url)
                if yt_url:
                    part = _youtube_to_part(yt_url)
                    media_parts.append(part)
                    # YouTube links don't go through Files API, no URI to track
                    logger.info("Added YouTube link: %s", yt_url)
                    continue

                # Try downloading as media (will skip HTML pages)
                result = await _download_url(url)
                if result:
                    data, mime_type = result
                    filename = urlparse(url).path.split("/")[-1] or "url_media"
                    part, uri = await _upload_bytes_to_gemini(data, mime_type, filename, client)
                    media_parts.append(part)
                    file_uris.append(uri)
                    logger.info("Processed URL media: %s", url)

            except Exception as e:
                logger.error("Failed to process URL '%s': %s", url, e)

        return media_parts, file_uris

    async def _process_attachment(
        self,
        attachment,
        client: genai.Client,
    ) -> tuple[types.Part, str]:
        """Downloads a Discord attachment into memory and uploads to Gemini."""
        logger.info(
            "Processing attachment: %s (type: %s, size: %d)",
            attachment.filename,
            attachment.content_type,
            attachment.size,
        )

        # Read attachment bytes directly — no local file save
        data = await attachment.read()
        mime_type = attachment.content_type or "application/octet-stream"

        part, uri = await _upload_bytes_to_gemini(data, mime_type, attachment.filename, client)
        return part, uri
