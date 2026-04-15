import re
import asyncio
import logging

from openai import OpenAIError
from openai import OpenAI
from utils.logger import LoggerMixin


class TranslateWorkDescription(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        openai: OpenAI, 
        lock: asyncio.Lock
        ):
        
        self.openai = openai
        
        self._lock = lock
        
    @staticmethod
    def clean_description(text: str) -> str:
        
        text = text.strip()
        text = re.sub(r'\n{2,}', '\n', text)
        
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        
        return '\n'.join(lines)
    
    async def translate(self, text: str) -> str:
        
        if not text or not text.strip():
            return text
        
        try:
            
            async with self._lock:
                
                response = await self.openai.chat.completions.create(
                    model = "gpt-5.1",
                    messages = [
                        {"role": "system", "content": "Fordítsd le a kapott szöveget magyarra. \
                            Ha a szöveg már teljesen magyar, akkor változtatás nélkül add vissza. \
                            Ha a szöveg vegyes nyelvű (például félig angol, félig magyar), \
                            akkor azonosítsd a nem magyar részeket és csak azokat fordítsd le magyarra, \
                            a már magyar részeket hagyd változatlanul. \
                            Csak a fordított szöveget add vissza, semmi extra magyarázat vagy körítés nem kell. \
                            A technikai megnevezéseket helyesen fordítsd le. \
                            A cégneveket ne fordítsd le, hagyd eredeti formájukban."},
                        {"role": "user", "content": text}
                    ],
                )
            
            result = response.choices[0].message.content.strip()
            
            self.log.debug("Translated work description: %s -> %s" % (text[:80], result[:80]))
            
            return result
        
        except OpenAIError as e:
            
            self.log.error("OpenAI API error while translating work description: %s" % str(e))
            
            return text
