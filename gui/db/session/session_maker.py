import typing as t

if t.TYPE_CHECKING:
    from ..db import MySQLDatabase

from sqlalchemy.orm import sessionmaker

class SessionMaker(sessionmaker):
    
    def __init__(
        self,
        parent: 'MySQLDatabase',
        **kwags
        ) -> None:
        
        super().__init__(**kwags)
        
        self.parent = parent

    def __call__(self, session_name = None, **local_kw):
        
        local_kw["parent"] = self
        
        local_kw["session_name"] = session_name
        
        return super().__call__(**local_kw)