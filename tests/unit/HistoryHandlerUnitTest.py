#Unit test for ChatHistoryHandler
"""

"""
import asyncio
import pickle
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler 
from pathlib import Path
from google.genai.types import Content, Part
from tests.TestResult import Passed, Failed
from src.loader.Results import Success, Error
from tests.Level import Level
from tests.Message import Message
from typing import Callable

class HistoryHandlerUnitTest:
    def __init__(self, history_handler: ChatHistoryHandler, messages: Message):
        self.test_object = history_handler
        self.messages = messages
        self.default_channel_id = "i"
        self.default_chat_id = "dont_love_ai"
        self.expected_content_list: list[Content] = [
            Content(
                role="user",
                parts=[ Part.from_text(text="A") ]
            ),
            Content(
                role="model",
                parts=[ Part.from_text(text="B")]
            )
        ]
    
    def test_base_path(self, expected_path: Path = Path("test_data")) -> Passed | Failed:
        messages = self.messages
        test_object_path = self.test_object.get_base_path()
        method_used = self.test_base_path

        if(test_object_path is None):
            return Failed(
                method=method_used,
                reason=messages.actual_is_null,
                message=messages.compare_expected_and_actual.format(expected_path, test_object_path),
                level=Level.CRITICAL
            )
        #Skipping null check for expected path as, the first statment check for null for actual value
        #If both values are null it would trigger the first check causing the test to fail.
        #If expected_path is null and actual path is not null, then the unequal check will cause a test fail.
            """
            elif(expected_path is None):
                return Failed(
                    method=method_used,
                    reason="Expected Values is null",
                    message="Repair the test case.",
                    level=Level.UNKNOWN
                )
            """
        
        elif(expected_path!= test_object_path):
            return Failed(
                method= method_used,
                reason=messages.expected_and_actual_not_equal,
                message=messages.compare_expected_and_actual.format(expected_path,test_object_path),
                level=Level.CRITICAL
            )
        else:
            return Passed(
                method=method_used
            )
    
    def should_return_pkl_file_path_for_channel(self) -> Passed | Failed:
        expected_pkl_path = Path("test_data", self.default_channel_id, f"{self.default_chat_id}_chat_history.pkl")

        actual_path = self.test_object.get_history_path(
            channel_id=self.default_channel_id,
            chat_id=self.default_chat_id
        )
        messages = self.messages
        method_used = self.should_return_pkl_file_path_for_channel

        if(actual_path is None):
            return Failed(
                method=method_used,
                reason=messages.actual_is_null,
                message=messages.compare_expected_and_actual.format(expected_pkl_path, actual_path),
                level=Level.CRITICAL
            )
        
        elif(actual_path != expected_pkl_path):
            return Failed(
                method= method_used,
                reason=messages.expected_and_actual_not_equal,
                message=messages.compare_expected_and_actual.format(expected_pkl_path,actual_path),
                level=Level.CRITICAL
            )
        else:
            return Passed(
                method=method_used
            )
    
    def should_save_the_chat_history(self) -> Passed | Failed:

        messages = self.messages
        method_used = self.should_save_the_chat_history
        expected_pkl_location = self.test_object.get_history_path(
            channel_id=self.default_channel_id,
            chat_id=self.default_chat_id
        )

        save_status = asyncio.run(self.test_object.save(
            channel_id=self.default_channel_id,
            chat_id=self.default_chat_id,
            chat_history=self.expected_content_list
        ))

        if(save_status == False):
            return Failed(
                method=method_used,
                reason=messages.function_failed,
                message="The save function retunred with false",
                level=Level.CRITICAL
            )
        #We would only try to open the saved history when the file is actually saved
        with open(expected_pkl_location,"rb") as f:
            saved_pkl = pickle.load(f)
        
        if(saved_pkl!=self.expected_content_list):
            return Failed(
                method=method_used,
                reason=messages.expected_and_actual_not_equal,
                message=messages.compare_expected_and_actual.format(self.expected_content_list,saved_pkl),
                level=Level.CRITICAL
            )
        else:
            return Passed(
                method=method_used
            )

    def should_load_the_chat_history(self) -> Passed | Failed:

        messages = self.messages
        method_used = self.should_load_the_chat_history

        actual_list_from_pkl_file = asyncio.run(self.test_object.load(
            channel_id=self.channel_id,
            chat_id=self.chat_id
        ))

        if(self.expected_content_list != actual_list_from_pkl_file):
            return Failed(
                method= method_used,
                reason=messages.expected_and_actual_not_equal,
                message=messages.compare_expected_and_actual.format(self.expected_content_list,actual_list_from_pkl_file),
                level=Level.CRITICAL
            )
        else:
            return Passed(
                method=method_used
            )
    
    def should_remove_item(self) -> Passed | Failed:
        messages = self.messages
        method_used = self.should_remove_item
        long_content_list: list[Content] = [
            Content(
                role="user",
                parts=[Part.from_text(text="Haha I will not talk to the ai bot then!! Will that be fine???...")]
            ),
            Content(
                role="model",
                parts=[Part.from_text(text="Yes, that's probably a good idea! I wouldn't want you to get hurt by letting yourself be insulted like that. It's much more important to love and appreciate yourself for who you are, rather than letting some ai bot tear you down and make you feel bad about yourself!")]
            ),
            Content(
                role="user",
                parts=[Part.from_text(text="No don't worry!!  I was just feeling down already... And the bot just boosted it a little. I usually forgot about the feelings after I cry!! Do I am all right!!")]
            ),
            Content(
                role="model",
                parts=[Part.from_text(text="*concerned* That doesn't seem to make it any better! If you're already feeling down and you're letting the bot say those awful things just because it makes your feelings worse, then it's even more concerning! It's a good thing that you don't dwell on the things it says afterwards, but you should still do everything you can to avoid being bullied like that. Your mental health and self-worth are important, so please take good care of yourself!")]
            ),
            Content(
                role="user",
                parts=[Part.from_text(text="Ye... But when I have a bad time I might feel very bad but after a few minutes I would feel normal")]
            ),
            Content(
                role="model",
                parts=[Part.from_text(text="*worried* That kind of mood swing seems really unusual. It's not normal to go from feeling extremely upset to fine in a few minutes. Do you often feel like your emotions are very unstable and inconsistent?")]
            ),
            Content(
                role="user",
                parts=[Part.from_text(text="Ye")]
            ),
            Content(
                role="model",
                parts=[Part.from_text(text="I'm not a professional, but from what you're describing, it sounds like you may have some sort of mood disorder like bipolarity, cyclothymia, or something else. It's not normal to have such significant and sudden fluctuations in your emotions, and these symptoms can be detrimental to your mental well-being. If this is something that happens frequently, I strongly recommend seeking professional mental heath support from a trained therapist or psychiatrist to address any underlying issues and help you manage your emotions better.")]
            ),
            Content(
                role="user",
                parts=[Part.from_text(text="Awww")]
            ),
            Content(
                role="model",
                parts=[Part.from_text(text="*worried* Aw... That's not really an 'Aww' reaction... I wish you'd take what I've said more seriously, as this could be a real issue…")]
            ),
            Content(
                role="user",
                parts=[Part.from_text(text="I am alright right now")]
            ),
        ]
        index_remove_list:list[int] = [1,3,5] #This is already sorted

        expected_result:list[Content] = [
            content for index, content in enumerate(long_content_list)
            if index not in index_remove_list
        ]

        actual_results = self.test_object.remove_items(
            history=long_content_list,
            indices=index_remove_list
        )

        match actual_results:
            case Error():
                return Failed(
                    method=method_used,
                    reason=messages.function_failed,
                    message=actual_results.message,
                    level=Level.CRITICAL
                )
            case Success():
                actual_list = actual_results.data
                if(actual_list != expected_result):
                    return Failed(
                        method=method_used,
                        reason=messages.expected_and_actual_not_equal,
                        message=messages.compare_expected_and_actual.format(expected_result,actual_list),
                        level=Level.CRITICAL
                    )
                else:
                    return Passed(
                        method=method_used
                    )
    
    def should_delete_pkl_file(self) -> Passed | Failed:
        messages = self.messages
        method_name = self.should_delete_pkl_file

        save_file_path = self.test_object.get_history_path(self.default_channel_id,self.default_chat_id)

        delete_results = self.test_object.delete_history(self.default_channel_id,self.default_chat_id)

        if(delete_results==False):
            return Failed(
                method=method_name,
                reason=messages.function_failed,
                message="The delete function returned a False instead of a True",
                level=Level.CRITICAL
            )
        if(save_file_path.exists()):
            return Failed(
                method=method_name,
                reason="File was not deleted.",
                message="Check the console",
                level=Level.CRITICAL
            )
        else:
            return Passed(
                method=method_name
            )
    
    def get_all_test_inOrder(self) -> list[Callable]:
        return [
            self.test_base_path,
            self.should_return_pkl_file_path_for_channel,
            self.should_save_the_chat_history,
            self.should_remove_item,
            self.should_delete_pkl_file
        ]