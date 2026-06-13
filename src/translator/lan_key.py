from enum import StrEnum

class LangKey(StrEnum):
    #--MessageProcessor.py
    LAN_CODE = "lan_code"
    NO_API = "no_api_key_found"
    HELPFUL_ASSISTANT = "helpful_assistant"
    CHAT_LOCKED = "chat_locked"
    """
    Payload variables:
    - total=2
    - user_id
    - message_url
    """
    CHECK_FAIL_MEDIA_FILE = "check_fail_media_file"
    ERROR_REMOVE_HISTORY_MESS = "error_remove_history_message"
    FAILED_RESPONSE_FROM_MODEL = "failed_response_from_model"
    """
    payload variables:
    - total=1
    - clean_error_msg
    """
    EMPTY_RESPONSE_FROM_MODEL = "empty_response_from_model"
    NO_CANDIDATES_IN_RESPONSE = "no_candidates_in_response"
    NULL_CONTENT_IN_RESPONSE = "null_content_in_response"
    ERROR_ON_SAVE_CHAT = "error_on_save_chat"
    ERROR_ON_SAVE_MEDIA_TABLE = "error_on_save_media_table"
    """
    payload variable:
    - total=1
    - save_status
    """
    #MessageProcessor.py --

    #-- Repo

    # MediaHandler
    MEDIA_HANDLER_NOT_FOUND = "errors.media_handler.not_found"
    MEDIA_HANDLER_CHANNEL_NOT_FOUND = "errors.media_handler.channel_not_found"
    MEDIA_HANDLER_INTEGRITY_ERROR = "errors.media_handler.integrity_error"
    MEDIA_HANDLER_DATABASE_ERROR = "errors.media_handler.database_error"
    MEDIA_HANDLER_ADD_API_KEY = "solutions.media_handler.add_api_key"

    # WebhookInfo
    WEBHOOK_NOT_FOUND = "errors.webhook.not_found"
    WEBHOOK_CHANNEL_NOT_FOUND = "errors.webhook.channel_not_found"
    WEBHOOK_INTEGRITY_ERROR = "errors.webhook.integrity_error"
    WEBHOOK_DATABASE_ERROR = "errors.webhook.database_error"
    WEBHOOK_ADD_API_KEY = "solutions.webhook.add_api_key"

    # ChannelConfig
    CHANNEL_CONFIG_NOT_FOUND = "errors.channel_config.not_found"
    CHANNEL_CONFIG_INVALID_COLUMN = "errors.channel_config.invalid_column"
    CHANNEL_CONFIG_DATABASE_ERROR = "errors.channel_config.database_error"

    # Persona
    PERSONA_NOT_FOUND = "errors.persona.not_found"
    PERSONA_DATABASE_ERROR = "errors.persona.database_error"

    #Repo --

    #-- CommonCom(common commands)
    LAN_DATA_NOT_SUCCESSFUL = "lan_data_not_successful"
    API_REQUIRED = "api_required"
    WEBHOOK_NO_MANAGE_PERM = "webhook_no_manage_perm"
    """
    payload variable = 1
    - channel_id
    """
    FETCH_WEBHOOK_HTTP_ERROR = "fetch_webhook_http_error"
    WEBHOOK_LIST_UNKNOWN_ERROR = "webhook_list_unknown_error"
    NAME_CHECK_TOKEN = "name_check_token"
    DESC_CHECK_TOKEN = "desc_check_token"
    CHANNEL_CONFIG_UNKNOWN_ERROR = "channel_config_unknown_error"
    CHANNEL_CONFIG_NOT_SET = "channel_config_not_set"
    TOTAL_TOKEN_USED = "total_token_used"
    """
    payload variable = 1
    - total_token
    """
    COUNT_TOKEN_ERROR = "count_token_error"
    WEBHOOK_NOT_CONFIGURED = "webhook_not_configured"
    WEBHOOK_NO_HISTORY = "webhook_no_history"
    WEBHOOK_NO_SYSTEM_INFO = "webhook_no_system_info"
    CHECK_TOKEN_SELECT_BOT = "check_token_select_bot"

    NAME_INFO = "name_info"
    DESC_INFO = "desc_info"
    INFO_STRING_VALUE = "info_string_value"
    """
    payload variables = 3
    - api_state
    - model_name
    - lan_code
    """
    NAME_PING = "name_ping"
    DESC_PING = "desc_ping"
    LATENCY = "latency"
    """
    payload variable = 1
    latency
    """
    RESET_HISTORY_MENU = "reset_history_menu"
    WEBHOOK_SELECT = "webhook_select"
    WEBHOOK_REMOVE = "webhook_remove"
    RESET_MUL_ERROR = "reset_mul_error"
    RESET_HISTORY_FAIL = "reset_history_fail"
    RESET_MEDIA_HIS_FAIL = "reset_media_his_fail"
    RESET_HIS_DONE = "reset_his_done"

    # -- WebhookCom
    IMAGE_MAX_SIZE_EXCEED = "image_max_size_exceed"
    """
    payload variables = 2
    - max_allowed_mb
    - current_image_size
    """
    IMAGE_NOT_PNG = "image_not_png"
    """
    payload variables = 1
    - file_type
    """
    CHAR_DEF_NOT_FOUND = "char_def_not_found"
    CHAR_DEF_DECODE_FAILED = "char_def_decode_fail"

    WEBHOOK_NO_DM = "webhook_no_dm"
    NO_WEBHOOK_FOUND = "no_webhook_found"
    WEBHOOK_NO_MANAGE_PERM_CHANNEL = "webhook_no_manage_perm_channel"
    """
    Payload variables:
    - total=1
    - channel_name
    """
    WEBHOOK_EMPTY_SYSTEM_INSTRUCTIONS = "webhook_empty_system_instructions"
    TEXT_FILE_NOT_TEXT = "text_file_not_text"
    TEXT_FILE_SIZE_EXCEEDED = "text_file_size_exceeded"
    """
    Payload variables:
    - total=2
    - max_size
    - current_size
    """
    IMAGE_INVALID_FORMAT = "image_invalid_format"
    IMAGE_SIZE_EXCEEDED = "image_size_exceeded"
    """
    Payload variables:
    - total=2
    - max_size_mb
    - current_size
    """
    WEBHOOK_DB_SAVE_FAILED = "webhook_db_save_failed"
    WEBHOOK_READY = "webhook_ready"
    """
    Payload variables:
    - total=1
    - webhook_id
    """
    WEBHOOK_START_CONVERSATION = "webhook_start_conversation"
    WEBHOOK_NO_CREATE_PERM = "webhook_no_create_perm"
    """
    Payload variables:
    - total=1
    - channel_id
    """
    DISCORD_INTERACTION_ERROR = "discord_interaction_error"
    UNEXPECTED_ERROR = "unexpected_error"
    WEBHOOK_DELETE_DB_INCONSISTENCY = "webhook_delete_db_inconsistency"
    """
    Payload variables:
    - total=1
    - webhook_name
    """
    WEBHOOK_REMOVED = "webhook_removed"
    """
    Payload variables:
    - total=1
    - webhook_name
    """
    WEBHOOK_NOT_EXIST_ALREADY_DELETED = "webhook_not_exist_already_deleted"
    HTTP_ERROR = "http_error"
    SELECT_TO_REMOVE = "select_to_remove"
    WEBHOOK_NO_DMS = "webhook_no_dms"
    NO_WEBHOOK_FOUND_IN_CHANNEL = "no_webhook_found_in_channel"
    WEBHOOK_DELETE_DB_FAILED = "webhook_delete_db_failed"
    """
    Payload variables:
    - total=1
    - webhook_name
    """
    WEBHOOKS_DELETED = "webhooks_deleted"
    """
    Payload variables:
    - total=1
    - total_deleted
    """
    HTTP_ERROR_MSG = "http_error_msg"
    SELECT_WEBHOOK_TO_KEEP = "select_webhook_to_keep"
    IMAGE_PROCESSING_ERROR = "image_processing_error"
    """
    Payload variables:
    - total=1
    - error_msg
    """
    V2_CHAR_DESCRIPTION = "v2_char_description"
    """
    Payload variables:
    - total=2
    - char_name
    - char_desc
    """
    V2_CHAR_SCENARIO = "v2_char_scenario"
    """
    Payload variables:
    - total=2
    - char_name
    - char_scenario
    """
    V2_CHAR_SYSTEM_PROMPT = "v2_char_system_prompt"
    """
    Payload variables:
    - total=1
    - char_prompt
    """
    V2_CHAR_MESSAGE_EXAMPLE = "v2_char_message_example"
    """
    Payload variables:
    - total=1
    - mess_example
    """
    V2_CHAR_NAME_INS = "v2_char_name_ins"
    """
    Payload variables:
    - total=1
    - char_name
    """
    WEBHOOK_INFO_SAVE_FAILED_DELETING = "webhook_info_save_failed_deleting"
    NO_CHANNEL_CONFIG_SAVED = "no_channel_config_saved"
    API_KEY_EMPTY = "api_key_empty"
    PERSONA_IMAGE_TOO_LARGE = "persona_image_too_large"
    WEBHOOK_CHAT_HISTORY_SAVE_FAILED = "webhook_chat_history_save_failed"
    WEBHOOK_INFO_SAVE_FAILED_DELETING_CREATED = "webhook_info_save_failed_deleting_created"
    WEBHOOK_CREATED_SUCCESS = "webhook_created_success"

    INLINE_PROMPT_1 = "inline_prompt_1"
    INLINE_PROMPT_2 = "inline_prompt_2"
    INLINE_PROMPT_3 = "inline_prompt_3"
    INLINE_PROMPT_4 = "inline_prompt_4"

    PERSONA_IMAGE_1 = "persona_image_1"
    """
    payload variable = 1
    - user_id
    """
    PERSONA_FAKE_RESPONSE = "persona_prompt_fake_model_response"
    """
    payload variable = 1
    - user_id
    """
    PERSONA_PROMPT_2="persona_prompt_2"
    FIRST_ROLEPLAY_INSTRUCTION = "first_roleplay_ins"
    """
    payload variable = 
    - char_name
    - user_id
    - description
    - scenario
    - message_example
    """

    CONFIG_DROPDOWN_EXCEED_LIMIT = "config_dropdown_exceed_limit"
    CONFIG_MODIFY_MODEL_ERROR = "config_modify_model_error"
    """
    Payload variables:
    - total=1
    - error_msg
    """
    CONFIG_MODIFY_MODEL_SUCCESS = "config_modify_model_success"
    """
    Payload variables:
    - total=2
    - model_name
    - channel_id
    """
    CONFIG_MODIFY_LANGUAGE_ERROR = "config_modify_language_error"
    """
    Payload variables:
    - total=3
    - error_msg
    - error_code
    - solution_msg
    """
    CONFIG_MODIFY_LANGUAGE_SUCCESS = "config_modify_language_success"
    """
    Payload variables:
    - total=2
    - language_code
    - channel_id
    """
    CONFIG_SAVE_API_ERROR = "config_save_api_error"
    """
    Payload variables:
    - total=3
    - error_msg
    - error_code
    - solution_msg
    """
    CONFIG_SAVE_API_SUCCESS = "config_save_api_success"
    """
    Payload variables:
    - total=2
    - channel_id
    - user_id
    """