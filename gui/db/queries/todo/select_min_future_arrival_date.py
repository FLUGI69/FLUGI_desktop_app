from sqlalchemy import select, func
from datetime import datetime
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from config import Config

class select_min_future_arrival_date(AsyncQueryBase):

    async def query(self) -> t.Optional[datetime]:
        
        now = datetime.now(Config.time.timezone_utc)
        
        query_result = (
            select(
                func.min(
                    
                    example_db.schedule.arrived_date
                )
            ).where(
                
                example_db.schedule.arrived_date >= now
            )
        )
        
        result = await self.session.execute(query_result)
        
        next_arrival = result.scalar()
        
        return next_arrival
