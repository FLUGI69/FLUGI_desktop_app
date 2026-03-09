from sqlalchemy import update, and_

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_calendar_by_id(AsyncQueryBase):

    async def query(self, id: int):
        
        query_result = (
            update(
                
                example_db.calendar
                
            ).where(
                
                and_(
                    example_db.calendar.id == id,
                    example_db.calendar.used == False
                )
                
            ).values(
                
                used = True
            )
        )

        await self.session.execute(query_result)
        
        await self.session.commit()