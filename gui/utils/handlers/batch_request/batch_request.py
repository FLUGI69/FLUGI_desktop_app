import logging

from utils.logger import LoggerMixin

class BatchCallbackHandler(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self):
        
        self.results = []
        
        self.errors = []

    def handle(self, request_id, response, exception):
        
        if exception:
            
            self.log.error("Batch error for request_id = %s: %s", 
                request_id, 
                exception
            )
            
            self.errors.append((request_id, exception))
            
            self.results.append(None)
            
            return
        
        self.results.append(response)