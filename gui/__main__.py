import os
import sys

if os.name == "nt":
    
    try:
        
        _real_stderr_fd = os.dup(2)
        _devnull_fd = os.open(os.devnull, os.O_WRONLY)
        
        os.dup2(_devnull_fd, 2)
        os.close(_devnull_fd)
        
        sys.stderr = os.fdopen(_real_stderr_fd, "w", closefd = False)
        
    except OSError:
        pass

from interfaces import Init
from interfaces import Interfaces

if __name__ == "__main__":
    
    init = Init()
    
    init.monkey_patch()
    
    init.config_reference_check()
    
    qt_app = Init.pyqt_application()

    try:
        
        Interfaces.run(qt_app)
  
    except Exception as e:
        
        init.log.exception("Unhandled exception: %s" % str(e))