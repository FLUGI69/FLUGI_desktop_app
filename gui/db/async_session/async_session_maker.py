from sqlalchemy.ext.asyncio import async_sessionmaker
import typing as t

if t.TYPE_CHECKING:
    
    from ..db import MySQLDatabase
    
class AsyncSessionMaker(async_sessionmaker):
    
    def __init__(self, parent: 'MySQLDatabase', **kwargs):
        
        super().__init__(**kwargs)
        
        self.parent = parent

    def __call__(self, session_name = None, **local_kw):
        
        local_kw["parent"] = self
        
        local_kw["session_name"] = session_name
        
        return super().__call__(**local_kw)
