def fixed_poll(self, timeout = None, logger = None):
    
    try:
        
        result = fixed_poll.original(self, timeout)
        
        for ov in getattr(self, "_unregistered", []):
            
            self._cache.pop(ov.address, None)
            
        self._unregistered.clear()
        
        return result
    
    except OSError as e:
        
        if getattr(e, "winerror", None) == 995:
            
            logger.debug("Suppressed WinError 995 in _IocpProactor._poll")
                
            return []
        
        raise

def patch_iocpproactor_poll(_IocpProactor, logger):
    
    if not hasattr(_IocpProactor, "_hotfixed"):
        
        fixed_poll.original = _IocpProactor._poll
        
        _IocpProactor._poll = lambda self, timeout = None: fixed_poll(self, timeout, logger)
        _IocpProactor._hotfixed = True
        
        logger.debug("Patched _IocpProactor._poll to fix memory leak")