from dataclasses import dataclass

@dataclass
class EntityMediaHandler:
    chat_id:str
    channel_id:str
    timestamp: int
    index_in_history: int