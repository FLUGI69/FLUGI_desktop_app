from sqlalchemy import update, and_
from datetime import datetime, timedelta

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_reminder_datetime_by_id(AsyncQueryBase):

    async def query(self, id: int, datetime: datetime):
        
        query_result = (
            update(
                
                example_db.calendar
                
            ).where(
                
                and_(
                    example_db.calendar.id == id,
                    example_db.calendar.used == False
                )
                
            ).values(
                
                reminder_date = datetime + timedelta(minutes = 5)
            )
        )

        await self.session.execute(query_result)
        
        await self.session.commit()
        
        