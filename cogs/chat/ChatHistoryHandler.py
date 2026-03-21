import os
import pickle
import aiofiles
from pathlib import Path
from google.genai.chats import AsyncChat
from loader.Results import Success, Error


class ChatHistoryHandler:
    """
    Manages per-channel chat history using pickle files.
    
    File structure:
        base_path / server_id / channel_id / chat_history.pkl
    """

    def __init__(self, base_path: Path):
        self.base_path: Path = Path(base_path)

    def get_history_path(self, channel_id: str, chat_id:str) -> Path:
        """Returns the full path to the chat history pickle file, creating directories if needed."""
        directory = self.base_path / channel_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{chat_id}_chat_history.pkl"

    async def load(self, channel_id: str, chat_id: str):
        """Loads chat history from the pickle file. Returns [] if missing or corrupt."""
        path = self.get_history_path(channel_id, chat_id)

        if not path.exists():
            return []

        try:
            async with aiofiles.open(path, "rb") as f:
                data = await f.read()
                return pickle.loads(data) if data else []
        except Exception as e:
            print(f"Failed to load chat history from {path}: {e}")
            return []

    async def save(self, channel_id: str, chat_id: str, chat_history) -> bool:
        """Save the chat history as a pickle file."""
        path = self.get_history_path(channel_id, chat_id)

        try:
            async with aiofiles.open(path, "wb") as f:
                await f.write(pickle.dumps(chat_history))
            return True
        except Exception as e:
            print(f"Failed to save chat history to {path}: {e}")
            return False

    def delete_history(self, channel_id: str, chat_id: str) -> bool:
        """Deletes the chat history file if it exists."""
        path = self.get_history_path(channel_id, chat_id)

        try:
            if path.exists():
                path.unlink()  # deletes the file
            return True
        except Exception as e:
            print(f"Failed to delete history at {path}: {e}")
            return False

    @staticmethod
    def remove_items(history: list[any], indices: list[int]) -> Success[AsyncChat] | Error:
        """Removes items at the given indices from the chat's curated history.

        Uses Python's built-in Timsort (optimal when the list is already sorted),
        then removes in reverse order to avoid index shifting.
        """
        #already a list
        #history = getattr(chat, '_curated_history', None)
        if history is None:
            return Error(message="Invalid chat object: missing _curated_history.")

        if not history:
            return Error(message="Chat history is empty.")

        indices.sort()  # Timsort — O(n) if already sorted

        for idx in indices:
            if idx < 0 or idx >= len(history):
                return Error(message=f"Index {idx} is out of range (0-{len(history) - 1}).")

        for idx in reversed(indices):
            history.pop(idx)

        return Success(data=history)
