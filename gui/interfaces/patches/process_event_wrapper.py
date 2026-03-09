class ProcessEventsWrapper:
    
    def __init__(self, outer, original):
        
        self._outer = outer
        
        self._original = original

    def __call__(self, self_obj, transferred, key, ov):
        
        return self._outer._patched_process_events(
            self._original,
            self_obj,
            transferred,
            key,
            ov
        )