from sqlalchemy import select, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.engine import Row

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
# TODO rewrite this query 
class select_all_works(AsyncQueryBase):

    async def query(self) -> list:
    
        query_result = (
            select(
                
                example_db.boat
                
            ).where(
                
                exists().where(
                    example_db.work.boat_id == example_db.boat.id
                )
            ).options(
                
                selectinload(
                    
                    example_db.boat.works
                )
            )
        )

        result = await self.session.execute(query_result)
        
        return result.all()
        