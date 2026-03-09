from sqlalchemy import select
from sqlalchemy.orm import selectinload, with_loader_criteria

from datetime import datetime 
import typing as t 

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_boat_work_by_boat_name(AsyncQueryBase):

    async def query(self, boat_name: str) -> t.Sequence[example_db.work]:
        
        name = f"%{boat_name}%"

        query_result = (
            select(
                
                example_db.work
                
            ).join(
                
                example_db.boat
                
            ).where(
                
                example_db.boat.name.like(name),
                example_db.work.finished_date.is_(None)
                
            ).options(
                selectinload(example_db.work.boat),
                selectinload(example_db.work.status).selectinload(example_db.work_status.notes),
                selectinload(example_db.work.images),
                selectinload(example_db.work.work_accessories)
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()
 