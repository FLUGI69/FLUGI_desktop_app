import typing as t

from .async_query_base import AsyncQueryBase

if t.TYPE_CHECKING:
    
    from ..db import MySQLDatabase

class AsyncQueryCallback:

    def __init__(self,
        db: 'MySQLDatabase',        
        query_attr: AsyncQueryBase
        ) -> None:
        
        self.db = db
        
        self.query_attr = query_attr

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:

        query: AsyncQueryBase = self.query_attr(db = self.db)
        
        return await query(*args, **kwargs)