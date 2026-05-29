from google.genai.types import Content, Part
from tests.TestResult import Passed, Failed
from tests.Message import Message
from tests.Level import Level
from typing import Callable

class ModuleTest:
    def __init__(self, messages: Message):
        self.first_content_list:list[Content] = [Content(role="user",parts=[Part.from_text(text="A")])]
        self.second_content_list:list[Content] = [Content(role="user",parts=[Part.from_text(text="B")])]
        self.third_content_list:list[Content] = [Content(role="user",parts=[Part.from_text(text="A")])]
        self.messages: Message = messages

    def check_if_module_have_eq(self):
        if (self.first_content_list == self.third_content_list):
            if(self.first_content_list!=self.second_content_list):
                return Passed(
                    method=self.check_if_module_have_eq
                )
        return Failed(
            method=self.check_if_module_have_eq,
            reason="__eq__ have changed for Content module. Other test might fail",
            message=f"{self.first_content_list}\n{self.second_content_list}\n{self.third_content_list}",
            level=Level.CRITICAL
        )
    def get_all_test_in_order(self) -> list[Callable]:
        return [
            self.check_if_module_have_eq
        ]