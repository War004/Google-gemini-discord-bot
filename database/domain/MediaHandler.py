from dataclasses import dataclass

@dataclass
class MediaHandler:
    chat_id:str
    channel_id:str
    timestamp: int
    index_in_history: int