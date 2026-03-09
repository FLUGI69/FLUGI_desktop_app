from sqlalchemy import select, and_
from datetime import timedelta, datetime

import typing as t 

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_reminders_data(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.calendar]:
    
        query_result = (
            select(
                
                example_db.calendar
                
            ).where(
                
                example_db.calendar.used == False
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()
        