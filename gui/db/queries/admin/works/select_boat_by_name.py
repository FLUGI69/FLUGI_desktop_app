from sqlalchemy import select
import typing as t 
from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_boat_by_name(AsyncQueryBase):

    async def query(self, boat_name: str) -> t.Sequence[example_db.boat]:
        
        name = f"%{boat_name}%"
        
        query_result = (
            select(
                
                example_db.boat
                
            ).where(
                
                example_db.boat.name.like(name)
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()
        