#hold the chat_id of the active chats to prevent race conditions
class ChatLock:
    def __init__(self):
        self.active_chats_id: set[str] = set()
    
    def add_chat_to_lock(self, chat_id: str) -> bool:
        if chat_id in self.active_chats_id:
            return False
        
        self.active_chats_id.add(chat_id)
        return True
    
    def unlock_chat(self,chat_id: str) -> bool:
        self.active_chats_id.remove(chat_id)