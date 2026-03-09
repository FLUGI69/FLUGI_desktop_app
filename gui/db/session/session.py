from sqlalchemy.orm import Session as BaseSession
import typing as t

if t.TYPE_CHECKING:
    from ..db import MySQLDatabase
    
from .session_maker import SessionMaker

class Session(BaseSession):

    tables: 'MySQLDatabase.tables'

    def __init__(self, 
        parent: SessionMaker, 
        session_name: None = None, 
        **kwags
        ) -> None:
        
        super().__init__(**kwags)
        
        self.parent = parent
        
        self.session_name = session_name
        
        self.tables = self.parent.parent.tables

        if self.parent.parent.queryTimer == True:
            
            self.timerStart = self.parent.parent.Timer.start()

    def close(self):

        if self.parent.parent.queryTimer == True:
            
            if self.session_name is not None:
                
                funcName = "Session - %s" % str(self.session_name)
                
            else:
                
                funcName = "Session"
                
            self.parent.parent.timerLog(funcName, self.timerStart)

        return super().close()