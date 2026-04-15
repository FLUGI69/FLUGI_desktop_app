from openai import OpenAIError
import asyncio
import logging
import typing as t

from utils.logger import LoggerMixin

if t.TYPE_CHECKING:
    
    from view.main_window import MainWindow

class OpenapiTranslate(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        main_window: 'MainWindow'
        ) -> None:
        
        super().__init__()
        
        self._lock = main_window.app.openapi_lock
        
        self.openai = main_window.app.openai
        
    async def translate_language(self, text: str, language: str):
        
        try:
        
            async with self._lock:    
                
                response = await self.openai.chat.completions.create(
                    model = "gpt-5.1",  
                    messages = [
                        {"role": "system", "content": f"Fordítsd le a felhasználó szövegét pontosan {language} nyelvre. \
                            Ügyelj a pontos fordításra. Csak a lefordított szöveget add vissza, semmi mást."},
                        {"role": "user", "content": text}
                    ],
                )
            
            result = response.choices[0].message.content.strip()

            self.log.debug("ChatGPT result: %s" % (str(result)))

            return result

        except OpenAIError as e: 
            
            self.log.error("OpenAI API error while handle PDF information: %s" % (str(e)))
