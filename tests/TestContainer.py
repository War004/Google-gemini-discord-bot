from pathlib import Path
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from tests.Message import Message

class TestContainer:
    def __init__(self,chat_history_handler: ChatHistoryHandler, messages: Message):
        self.chat_history_handler: ChatHistoryHandler = chat_history_handler
        self.messages: Message = messages