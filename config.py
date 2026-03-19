import discord


model_list = [
    {"Gemini 3.1 pro preview":"gemini-3.1-pro-preview"},
    {"Gemini 3 flash preview":"gemini-3-flash-preview"},
    {"Gemini 3.1 flash lite preview": "gemini-3.1-flash-lite-preview"},
    {"Gemini 2.5 pro":"gemini-2.5-pro"},
    {"Gemini 2.5 flash":"gemini-2.5-flash"},
    {"Gemini 2.5 flash lite":"gemini-2.5-flash-lite"},
    #{"Gemini 2.0 flash":"gemini-2.0-flash"},
    #{"Gemini 2.0 flash lite":"gemini-2.0-flash-lite"},
]


MODEL_LIST = [
    discord.app_commands.Choice(name=key,value=value)
    for item in model_list
    for key,value in item.items()
][:25]
lan_list = [
{"Assamese": "as"},
    {"Bengali": "bn"},
    {"English": "en"},
    {"French": "fr"},
    {"Gujarati": "gu"},
    {"Hindi": "hi"},
    {"Japanese": "ja"},
    {"Kannada": "kn"},
    {"Maithili": "mai"},
    {"Malayalam": "mal"},
    {"Meitei": "mni"},
    {"Marathi": "mr"},
    {"Nepali": "ne"},
    {"Russian": "ru"},
    {"Tamil": "ta"}
]
LAN_LIST = [
    discord.app_commands.Choice(name=key,value=value)
    for item in lan_list
    for key, value in item.items()
][:25]
