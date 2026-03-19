from dataclasses import dataclass

@dataclass
class EntityChannelConfig:
    channel_id: str
    api_key: str | None = None
    model_name: str | None = None
    default_lan_code: str | None = None
    r18_enabled: bool = False