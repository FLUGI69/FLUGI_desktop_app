from sqlalchemy import select
from sqlalchemy.orm import noload

import typing as t 

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_all_boats(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.boat]:
    
        query_result = (
            select(
                
                example_db.boat
                
            ).options(
                
                noload(example_db.boat.works),
                noload(example_db.boat.schedule)
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()
        