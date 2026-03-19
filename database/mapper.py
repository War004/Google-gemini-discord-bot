from database.domain.ChannelConfig import ChannelConfig
from database.domain.WebhookInfo import WebhookInfo
from database.domain.Persona import Persona
from database.domain.MediaHandler import MediaHandler
from database.entity.EntityChannelConfig import EntityChannelConfig
from database.entity.EntityWebhookInfo import EntityWebhookInfo
from database.entity.EntityPersona import EntityPersona
from database.entity.EntityMediaHandler import EntityMediaHandler


# ── ChannelConfig ─────────────────────────────────────────────

def channel_config_to_entity(item: ChannelConfig) -> EntityChannelConfig:
    return EntityChannelConfig(
        channel_id=item.channel_id,
        api_key=item.api_key,
        model_name=item.model_name,
        default_lan_code=item.default_lan_code,
        r18_enabled=item.r18_enabled,
    )

def channel_config_to_item(entity: EntityChannelConfig) -> ChannelConfig:
    return ChannelConfig(
        channel_id=entity.channel_id,
        api_key=entity.api_key,
        model_name=entity.model_name,
        default_lan_code=entity.default_lan_code,
        r18_enabled=entity.r18_enabled,
    )


# ── WebhookInfo ───────────────────────────────────────────────

def webhook_info_to_entity(item: WebhookInfo) -> EntityWebhookInfo:
    return EntityWebhookInfo(
        bot_id=item.webhook_id,
        channel_id=item.channel_id,
        bot_info=item.webhook_system_information,
    )

def webhook_info_to_item(entity: EntityWebhookInfo) -> WebhookInfo:
    return WebhookInfo(
        webhook_id=entity.bot_id,
        channel_id=entity.channel_id,
        webhook_system_information=entity.bot_info,
    )


# ── Persona ───────────────────────────────────────────────────

def persona_to_entity(item: Persona) -> EntityPersona:
    return EntityPersona(
        hash=item.hash,
        information=item.information,
    )

def persona_to_item(entity: EntityPersona) -> Persona:
    return Persona(
        hash=entity.hash,
        information=entity.information,
    )


# ── MediaHandler ──────────────────────────────────────────────

def media_handler_to_entity(item: MediaHandler) -> EntityMediaHandler:
    return EntityMediaHandler(
        chat_id=item.chat_id,
        channel_id=item.channel_id,
        timestamp=item.timestamp,
        index_in_history=item.index_in_history,
    )

def media_handler_to_item(entity: EntityMediaHandler) -> MediaHandler:
    return MediaHandler(
        chat_id=entity.chat_id,
        channel_id=entity.channel_id,
        timestamp=entity.timestamp,
        index_in_history=entity.index_in_history,
    )
