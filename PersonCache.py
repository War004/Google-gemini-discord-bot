import asyncio
import imagehash
from PIL import Image

class PersonCache:
    def __init__(self):
        self._persona_cache: dict[str,str] = {}
        
    def getValue(self,key:str)-> str | None:
        return self._persona_cache.get(key)
    
    def updateValue(self,key:str,person_details:str):
        self._persona_cache[key] = person_details
    
    def delValue(self,key:str):
        del self._persona_cache[key]
    
    @staticmethod
    async def getImageHash(img:Image)-> str:
        hash_obj = await asyncio.to_thread(lambda: imagehash.phash(img, hash_size=4))
        return str(hash_obj)