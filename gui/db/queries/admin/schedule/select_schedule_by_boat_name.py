from sqlalchemy import select
from sqlalchemy.orm import selectinload, noload

from datetime import datetime
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from config import Config

class select_schedule_by_boat_name(AsyncQueryBase):

    async def query(self, boat_name: str) -> t.Sequence[example_db.boat]:
        
        now = datetime.now(Config.time.timezone_utc)
        
        name = f"%{boat_name}%"
        
        query_result = (
            select(
                
                example_db.boat
                
            ).options(
                
                selectinload(example_db.boat.schedule), 
                noload(example_db.boat.works) 
                
            ).where(
                
                example_db.boat.name.ilike(name),
                example_db.boat.schedule.any(
                    example_db.schedule.leave_date > now
                )
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().unique().all()
        