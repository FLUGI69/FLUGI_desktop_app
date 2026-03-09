import traceback
from abc import ABC, abstractmethod
import logging
from ..async_session import AsyncSession
import typing as t

if t.TYPE_CHECKING:
    
    from ..db import MySQLDatabase
    
class AsyncQueryBase(ABC):
    
    log: logging.Logger
    
    session_name: str = None
    
    log = None
    
    tables = None
    
    session: AsyncSession = None 

    def __init__(self, db: 'MySQLDatabase' = None):
        
        self.db = db
        
        if self.tables is None:
            
            self.tables = self.db.tables
            
        if self.log is None:
            
            self.log = self.db.log
            
        if self.session_name is None:
            
            self.session_name = self.__class__.__name__
            
        if self.db.Session is not None:

            self.log.debug("BEGIN AsyncSession -> %s " % (str(self.session_name)), stacklevel = 5)

            self.session = self.db.AsyncSession(session_name = self.session_name)

    async def __call__(self, *args, **kwargs):
        
        async with self.db.AsyncSession(session_name = self.session_name) as session:
            
            self.session = session
        
            try:
        
                return await self.query(*args, **kwargs)
            
            except Exception:
                
                self.log.error(traceback.format_exc())
                
                await self.__safe_rollback()
                
                raise
            
            finally:
                
                self.log.debug("END AsyncSession -> %s" % self.session_name)

    async def __safe_rollback(self):
        
        try:
            
            await self.session.rollback()
            
            self.log.debug("Transaction rolled back successfully")
            
        except Exception as e:
            
            self.log.exception("Rollback failed: %s" % str(e))

    @abstractmethod
    async def query(self, *args, **kwargs):
        pass

    def get_table(self, table_name: str):
        
        return getattr(self.db.tables, str(table_name))