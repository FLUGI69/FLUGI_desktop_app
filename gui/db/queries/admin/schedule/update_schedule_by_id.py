from sqlalchemy import update, and_

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_schedule_by_id(AsyncQueryBase):

    async def query(self, 
        id: int, 
        values_to_update: dict
        ) -> None:

        query_result = (
            update(
                
                example_db.schedule
                
            ).where(
                
                example_db.schedule.id == id
                
            ).values(
                
                **values_to_update
            )
        )

        await self.session.execute(query_result)
        
        await self.session.commit()