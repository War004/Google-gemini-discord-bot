from dataclasses import dataclass
@dataclass
class PngParserResults:
    name:str
    profileImage: bytes
    description:str
    scenario:str
    system_prompt:str
    message_example:str
    first_message:str