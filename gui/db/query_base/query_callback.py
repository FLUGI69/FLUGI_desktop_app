import typing as t
from abc import ABC, abstractmethod
import typing as t

if t.TYPE_CHECKING:
    from ..db import MySQLDatabase

from .query_base import QueryBase
    
class QueryCallback:

    def __init__(self,
        db: 'MySQLDatabase',
        query_attr: QueryBase
        ) -> None:
        
        self.db = db
        
        self.query_attr = query_attr

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:

        query: QueryBase = self.query_attr(db = self.db)
        
        return query(*args, **kwargs)