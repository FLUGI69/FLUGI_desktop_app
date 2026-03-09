from sqlalchemy import insert
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_reminder(AsyncQueryBase):

    async def query(self, note: str, reminder_date: datetime, used: bool) -> None:
    
        await self.session.execute(
            insert(
                
                example_db.calendar
                
            ).values(
                
                note = note,
                reminder_date = reminder_date,
                used = used
            )
        )
        
        await self.session.commit()
        
        