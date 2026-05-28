import json
from pathlib import Path
from loader.Results import *
from typing import Any
import aiofiles
import asyncio

class Json:
    def __init__(self):
        pass

    @staticmethod
    def load(direct_json_path: Path) -> Success[dict] | Error:
        try:
            if not direct_json_path.exists():
                #if file doesn't exists then make it
                print("The api file doesn't exists")
                print(f"Making one at {direct_json_path.absolute}")
                
                direct_json_path.parent.mkdir(parents=True, exist_ok=True)
                direct_json_path.write_text("{}", encoding="utf-8")
                return Success(data={})
            
            #open the class
            with open(direct_json_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return Success(data= data)
        
        except json.JSONDecodeError as e:
            return Error(message="Corrupted JSON file", solution=f"Look at the file at {direct_json_path.absolute}",exception=e)
        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)
        
    @staticmethod
    def write(data: dict, direct_json_path: Path) -> Success[dict] | Error:
        try:
            if not direct_json_path.exists():
                #if file doesn't exists then make it
                print("The api file doesn't exists")
                print(f"Making one at {direct_json_path.absolute}")
                
                direct_json_path.parent.mkdir(parents=True, exist_ok=True)
                direct_json_path.write_text(data, encoding="utf-8")
                return Success(data=data)
            
            #directly overwrite
            direct_json_path.write_text(data, encoding="utf-8")
            return Success(data= data)
        
        except json.JSONDecodeError as e:
            return Error(message="Corrupted JSON file", solution=f"Look at the file at {direct_json_path.absolute}",exception=e)
        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)
    
    @staticmethod
    async def async_load(direct_json_path: Path) -> Success[dict] | Error:
        try:
            # Check if file exists asynchronously
            if not await asyncio.to_thread(direct_json_path.exists):
                print("The api file doesn't exists")
                print(f"Making one at {direct_json_path.absolute()}")

                #add choice later
                
                # Create parent directories
                await asyncio.to_thread(direct_json_path.parent.mkdir, parents=True, exist_ok=True)
                
                async with aiofiles.open(direct_json_path, mode='w', encoding="utf-8") as f:
                    await f.write("{}")
                return Success(data={})

            # Read the file asynchronously
            async with aiofiles.open(direct_json_path, mode='r', encoding="utf-8") as f:
                contents = await f.read()
                data = json.loads(contents)
                return Success(data=data)

        except json.JSONDecodeError as e:
            return Error(message="Corrupted JSON file", solution=f"Look at the file at {direct_json_path.absolute()}", exception=e)
        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)

    @staticmethod
    async def async_write(data: dict, direct_json_path: Path) -> Success[dict] | Error:
        try:
            # Ensure the directory exists
            await asyncio.to_thread(direct_json_path.parent.mkdir, parents=True, exist_ok=True)
            
            # Convert dict to string first
            json_string = json.dumps(data, indent=4)
            
            # Write to file asynchronously
            async with aiofiles.open(direct_json_path, mode='w', encoding="utf-8") as f:
                await f.write(json_string)
            
            return Success(data=data)

        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)
        
    async def async_remove_key(self,key: str, direct_json_path: Path) -> Success[dict] | Error:
        """
        **Only use str key**
        """
        try:
            #check if file exits or not
            if not direct_json_path.is_file():
                return Error(
                    message="The certain json file doesn't exist locally in device."
                )
            
            #open the file, if it exists.
            async with aiofiles.open(direct_json_path,mode='r',encoding="utf-8") as f:
                contents = await f.read()
            
            if key not in contents:
                return Error(message="Entry key not found",code=113, solution="Manually check the json")
            
            contents.pop(key)
            return Success(data=contents)
        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)
        
        
    async def async_remove_item_mediaHandler(self, key: str, item_index: int, direct_json_path: Path) -> Success[dict] | Error:
        """
        **Only use str key**
        Removes an item from a list inside the JSON based on its exact position (list_index).
        """
        try:
                # Check if file exists
                if not direct_json_path.is_file():
                    return Error(message="The specified json file doesn't exist locally.")
                
                # Open and read the file
                async with aiofiles.open(direct_json_path, mode='r', encoding="utf-8") as f:
                    raw_contents = await f.read()
                
                # Parse the string into a dictionary
                try:
                    contents = json.loads(raw_contents) if raw_contents.strip() else {}
                except json.JSONDecodeError:
                    return Error(message="File does not contain valid JSON", code=114)
                
                # Check if the chat_id (key) exists and holds a list
                if key not in contents:
                    return Error(message="Entry key not found", code=113)
                
                target_list = contents[key]
                if not isinstance(target_list, list):
                    return Error(message=f"Data under key '{key}' is not a list.")

                # --- THE SIMPLE REMOVAL LOGIC ---
                try:
                    # This directly deletes the item at the exact position you provide
                    target_list.pop(item_index)
                except IndexError:
                    # Failsafe: Triggers if you ask to delete item #10 but there are only 5 items
                    return Error(message=f"No item exists at position {item_index}.")
                # --------------------------------

                # Write the updated dictionary back to the JSON file
                async with aiofiles.open(direct_json_path, mode='w', encoding="utf-8") as f:
                    await f.write(json.dumps(contents, indent=4))
                
                return Success(data=contents)
        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)
        
    async def async_append_to_key(self, key: str, value: Any, direct_json_path: Path) -> Success[dict] | Error:
        """
        **Only use str key**
        Reads a JSON file, appends data to a list under the given key, and saves it.
        """
        try:
            # Check if file exists
            if not direct_json_path.is_file():
                return Error(
                    message="The specified json file doesn't exist locally in device."
                )
            
            # Open and read the file
            async with aiofiles.open(direct_json_path, mode='r', encoding="utf-8") as f:
                raw_contents = await f.read()
                
            # Parse the string into a dictionary 
            try:
                contents = json.loads(raw_contents) if raw_contents.strip() else {}
            except json.JSONDecodeError:
                return Error(message="File does not contain valid JSON", code=114)

            if key in contents:
                # If the existing data is already a list, append the new value to it
                if isinstance(contents[key], list):
                    contents[key].append(value)
                # If the data exists but is just a single dictionary (from your older code),
                # convert it into a list containing the old data AND the new data
                else:
                    contents[key] = [contents[key], value]
            else:
                # If the chat_id doesn't exist yet, start a brand new list with the value inside
                contents[key] = [value]
            # -----------------------------

            # Write the updated dictionary back to the JSON file
            async with aiofiles.open(direct_json_path, mode='w', encoding="utf-8") as f:
                await f.write(json.dumps(contents, indent=4))
                
            return Success(data=contents)
            
        except Exception as e:
            return Error(message="Unexpected file system error", exception=e)