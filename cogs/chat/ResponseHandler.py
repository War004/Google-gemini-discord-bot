import io
import re
import discord


async def extract_response_text(response):
    """
    Extracts text and image data from the Gemini API response.

    Returns:
        (text_response, image_data): A tuple.
            - text_response: Combined text, code, code output, and source links.
            - image_data: List of (mime_type, image_bytes) tuples, or None.
    """
    if not response or not response.candidates:
        return "No response from the model.", None

    first_candidate = response.candidates[0]

    # Guard: content or parts may be None when safety-blocked
    if not first_candidate.content or not first_candidate.content.parts:
        return "⚠️ Response was blocked by safety filters.", None

    parts = first_candidate.content.parts

    text_parts = []
    code_snippet = None
    code_output = None
    image_data = []

    for part in parts:
        if part.text:
            text_parts.append(part.text.strip())
        if part.executable_code:
            code_snippet = part.executable_code.code.strip()
        if part.code_execution_result:
            code_output = part.code_execution_result.output.strip()
        if part.inline_data and part.inline_data.mime_type.startswith('image/'):
            image_data.append((part.inline_data.mime_type, part.inline_data.data))

    combined_text = "\n".join(text_parts)

    # Extract grounding sources
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

    return text_response, image_data if image_data else None


def _extract_sources(candidate) -> list:
    """Extracts unique grounding source URLs from a Gemini response candidate."""
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
    return list(set(sources))


async def send_response(
    message: discord.Message,
    text_response: str,
    image_data=None,
    webhook: discord.Webhook = None,
) -> None:
    """
    Sends a response to the channel, handling Discord's 2000-char limit
    and optional image attachments.

    If ``webhook`` is provided, sends via the webhook instead of the channel.
    """
    # Decide the send target: webhook or channel
    async def _send(content=None, file=None):
        if webhook:
            if file:
                await webhook.send(content=content, file=file)
            else:
                await webhook.send(content=content)
        else:
            if content:
                await message.channel.send(content)
            if file:
                await message.channel.send(file=file)

    if not text_response:
        text_response = "No response from the model."

    # Send text (chunked if over 2000 chars)
    if len(text_response) <= 2000:
        await _send(content=text_response)
    else:
        chunks = re.findall(r".{1,2000}(?:\s|$)", text_response, re.DOTALL)
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                await _send(content=chunk)

    # Send images if present
    if image_data:
        for mime_type, image_bytes in image_data:
            try:
                filename = f"gemini_image.{mime_type.split('/')[-1]}"
                image_file = discord.File(io.BytesIO(image_bytes), filename=filename)
                await _send(file=image_file)
            except Exception as e:
                print(f"Failed to send image: {e}")
