import logging

class PollWrapper:
    
    def __init__(self, original_poll, logger: logging.Logger):
        
        self._original_poll = original_poll
        
        self._log = logger
        
    def __call__(self, self_obj, timeout = None):
        
        try:
            
            return self._original_poll(self_obj, timeout)
        
        except OSError as e:
            
            if getattr(e, "winerror", None) == 995:
                
                self._log.debug("Suppressed WinError 995 in fallback EventPoller._poll")
                
                return []
            
            raise