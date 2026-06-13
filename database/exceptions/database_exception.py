# ── Shared ────────────────────────────────────────────────────────────────────

class ChannelNotFoundError(Exception):
    """Raised when a referenced channel_id doesn't exist (FK violation).
    Shared by MediaHandlerDao and WebhookInfoDao."""
    pass


# ── MediaHandler ──────────────────────────────────────────────────────────────

class MediaHandlerNotFoundError(Exception):
    """Raised when a media_handler entry doesn't exist."""
    pass


class MediaHandlerIntegrityError(Exception):
    """Raised on a non-FK IntegrityError in media_handler."""
    pass


class MediaHandlerDatabaseError(Exception):
    """Raised on a generic DB failure in media_handler."""
    pass


# ── WebhookInfo ───────────────────────────────────────────────────────────────

class WebhookNotFoundError(Exception):
    """Raised when a webhook_info entry doesn't exist."""
    pass


class WebhookIntegrityError(Exception):
    """Raised on a non-FK IntegrityError in webhook_info."""
    pass


class WebhookDatabaseError(Exception):
    """Raised on a generic DB failure in webhook_info."""
    pass


# ── ChannelConfig ─────────────────────────────────────────────────────────────

class ChannelConfigNotFoundError(Exception):
    """Raised when a channel_config entry doesn't exist."""
    pass


class InvalidColumnError(Exception):
    """Raised when an invalid column name is passed to a field helper."""
    pass


class ChannelConfigDatabaseError(Exception):
    """Raised on a generic DB failure in channel_config."""
    pass


# ── Persona ───────────────────────────────────────────────────────────────────

class PersonaNotFoundError(Exception):
    """Raised when a persona entry doesn't exist."""
    pass


class PersonaDatabaseError(Exception):
    """Raised on a generic DB failure in persona."""
    pass