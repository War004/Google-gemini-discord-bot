from dataclasses import dataclass

@dataclass
class WebhookInfo:
    webhook_id:str
    channel_id:str
    webhook_system_information: str
