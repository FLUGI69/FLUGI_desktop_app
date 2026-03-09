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