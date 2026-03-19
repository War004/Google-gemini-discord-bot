from dataclasses import dataclass

@dataclass
class EntityWebhookInfo:
    bot_id:str
    channel_id:str
    bot_info:str