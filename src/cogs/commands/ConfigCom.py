import discord

from discord.ext import commands
from discord import app_commands
from src.loader.Results import Error,Success
import discord
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from src.translator.translator import Translator
from src.translator.lan_key import LangKey
from src.config import LAN_LIST, MODEL_LIST
from src.BloomFilter import BloomFilter

class ConfigCom(commands.Cog):
    def __init__(
            self,
            bot: commands.Bot,
            string_translator: Translator,
            channel_config_repo: ChannelConfigRepo,
            api_bloom: BloomFilter,
            lan_bloom: BloomFilter
            ):
        self.bot = bot
        self.string_translator = string_translator
        self.channel_repo = channel_config_repo
        self.api_bloom = api_bloom
        self.lan_bloom = lan_bloom
    
    async def create_dropdown(self, options_list: list[dict[str,str]], interaction: discord.Interaction, placeholder: str, lan_code: str, callback):

        if(len(options_list)> 25):
            msg = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.CONFIG_DROPDOWN_EXCEED_LIMIT,
                lan_code=lan_code
            )
            await interaction.followup.send(msg)

        try:
            # 1. Slice the list directly to get the first 25 items
            safe_items = options_list[:25]

            # 2. Extract the 'label' and 'value' from each dictionary in the list
            options = [
                discord.SelectOption(label=key, value=value) 
                for item in safe_items 
                for key, value in item.items()
            ]

            # 3. Use capital V for View()
            view = discord.ui.View()
            dropdown = discord.ui.Select(
                placeholder=placeholder,
                options=options
            )
            dropdown.callback = callback
            view.add_item(dropdown)

            return view
        except Exception as e:
            # [AutoFix] Replaced match type(e) with isinstance — match type(e) used structural
            # pattern matching, causing the first case to always match as a capture pattern.
            if isinstance(e, discord.Forbidden):
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_NO_MANAGE_PERM_CHANNEL,
                    lan_code=lan_code,
                    payload={
                        "channel_name": interaction.channel.name
                    }
                )
                await interaction.followup.send(msg)
            elif isinstance(e, discord.HTTPException):
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.FETCH_WEBHOOK_HTTP_ERROR,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
            else:
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_LIST_UNKNOWN_ERROR,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
            print(f"[ConfigCom] create_dropdown Exception: {type(e).__name__}: {e}")
            return None
        
    config_group = app_commands.Group(name="config", description="Config the configurable options")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        #This was added as hosting happens in India, latency is high between US and India
        await interaction.response.defer()
        requires_api = {}

        api_hit = self.api_bloom.check(interaction.channel_id)
        lan_hit = self.lan_bloom.check(interaction.channel_id)
        local_lan_code = str(interaction.locale).split("-")[0]
        
        if lan_hit:
            # NOTE: lan_code is not passed to DB repository methods because cogs use Success/Error wrapper checks for user-facing translations.
            db_result = await self.channel_repo.get_lan_code(interaction.channel_id)
            match db_result:
                case Success():
                    local_lan_code = db_result.data
                case Error():
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.LAN_DATA_NOT_SUCCESSFUL,
                        lan_code=local_lan_code
                    )
                    await interaction.followup.send(message)

        if interaction.command.name in requires_api:
            if api_hit == False:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.API_REQUIRED,
                    lan_code=local_lan_code
                )
                await interaction.followup.send(message)
                return False
        interaction.extras["lan_code"] = local_lan_code
        return True
                    
    @config_group.command(
        name=app_commands.locale_str("model"),
        description=app_commands.locale_str("Modify the model used for a channel")
    )
    @app_commands.choices(selected_model=MODEL_LIST)
    async def modify_model_used(self, interaction: discord.Interaction, selected_model: str):
        # selected_model now automatically contains the 'value' (e.g., 'gemini-pro')
        # The user's selection is passed directly into the function
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        # Save the new entry using the parameter
        # NOTE: lan_code is not passed to DB repository methods because cogs use Success/Error wrapper checks for user-facing translations.
        results = await self.channel_repo.update_model_name(
            channel_id=str(interaction.channel_id),
            model_name=selected_model
        )

        # Handle the results immediately
        match results:
            case Error():
                print("Error while modify the db entry for a channel")
                print(f"\n{results.message}\n{results.exception}\n")
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CONFIG_MODIFY_MODEL_ERROR,
                    lan_code=lan_code,
                    payload={
                        "error_msg": results.message
                    }
                )
                await interaction.followup.send(msg)
                
            case Success():
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CONFIG_MODIFY_MODEL_SUCCESS,
                    lan_code=lan_code,
                    payload={
                        "model_name": selected_model,
                        "channel_id": str(interaction.channel_id)
                    }
                )
                await interaction.followup.send(msg)
    
    @config_group.command(
        name=app_commands.locale_str("language"),
        description=app_commands.locale_str("Configure the language used on per Channel bases.")
    )
    @app_commands.choices(selected_language=LAN_LIST)
    async def modify_channel_langauge(self, interaction: discord.Interaction, selected_language: str):
        #selected language is the new choice, we will use this value directly instead of cheking the bloom filter and db
        #lan_code = interaction.extras.get(LangKey.LAN_CODE)

        #save the entry in the db
        # NOTE: lan_code is not passed to DB repository methods because cogs use Success/Error wrapper checks for user-facing translations.
        results = await self.channel_repo.update_lan_code(
            channel_id=str(interaction.channel_id),
            default_lan_code=selected_language
        )

        match results:
            case Error():
                print("Failed to save the default lan code in the db\n")
                print(f"Error message: {results.message}")
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CONFIG_MODIFY_LANGUAGE_ERROR,
                    lan_code=selected_language,
                    payload={
                        "error_msg": results.message,
                        "error_code": str(results.code),
                        "solution_msg": results.solution
                    }
                )
                await interaction.followup.send(msg)
            case Success():
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CONFIG_MODIFY_LANGUAGE_SUCCESS,
                    lan_code=selected_language,
                    payload={
                        "language_code": selected_language,
                        "channel_id": str(interaction.channel_id)
                    }
                )
                #Values are added on the repo level to the bloom filter if a success happens
                await interaction.followup.send(msg)

    @config_group.command(
        name=app_commands.locale_str("api-key"),
        description=app_commands.locale_str("Add an api key")
    )
    @app_commands.describe(
        api_key=app_commands.locale_str("[Don't share the api key with anyone] Google gemini api key")
    )
    async def set_api_key(self, interaction: discord.Interaction,api_key: str):
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        #save the entry in the db
        # NOTE: lan_code is not passed to DB repository methods because cogs use Success/Error wrapper checks for user-facing translations.
        result = await self.channel_repo.update_api_key(
            channel_id=str(interaction.channel_id),
            api_key=api_key
        )

        match result:
            case Error():
                print("Falied to save the api key in the db.\n")
                print(f"Error: {result.message}\n")
                print(f"{result.exception}\n")
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CONFIG_SAVE_API_ERROR,
                    lan_code=lan_code,
                    payload={
                        "error_msg": result.message,
                        "error_code": str(result.code),
                        "solution_msg": result.solution
                    }
                )
                await interaction.followup.send(msg)
            
            case Success():
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.CONFIG_SAVE_API_SUCCESS,
                    lan_code=lan_code,
                    payload={
                        "channel_id": str(interaction.channel_id),
                        "user_id": str(interaction.user.id)
                    }
                )
                #Values are added on the repo level to the bloom filter if a success happens
                await interaction.followup.send(msg)