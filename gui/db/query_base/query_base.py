import typing as t
from abc import ABC, abstractmethod
import logging

if t.TYPE_CHECKING:
    from ..db import MySQLDatabase

from ..session import Session
import traceback

class QueryBase(ABC):
    
    log: logging.Logger

    session_name: str = None
    
    log = None

    tables = None

    session: Session = None

    def __init__(self, db: 'MySQLDatabase') -> None:
        
        self.db = db

        if self.tables is None:
            
            self.tables = self.db.tables

        if self.log is None:
            
            self.log = self.db.log

        if self.session_name is None:
            
            self.session_name = self.__class__.__name__

        if self.db.Session is not None:

            self.log.debug("BEGIN Session -> %s " % (str(self.session_name)), stacklevel = 5)

            self.session = self.db.Session(session_name = self.session_name)

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:

        try:

            resp = self.query(*args, **kwargs)

            return resp

        except Exception as e:

            self.log.error("Error during session: %s" % (str(traceback.format_exc())))

        finally:

            self.session.close()

            self.log.debug("END Session -> %s " % (str(self.session_name)), stacklevel = 5)
            
    @abstractmethod
    def query(self):
        pass

    def get_table(self, table_name: str):

        return getattr(self.db.tables, str(table_name))