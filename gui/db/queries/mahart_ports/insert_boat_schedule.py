from sqlalchemy import insert, select, exists, and_
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_boat_schedule(AsyncQueryBase):

    async def query(self, 
        boat_id: int,
        location: str, 
        arrived_date: datetime, 
        ponton: str, 
        leave_date: datetime
        ):
        
        is_exist = await self._schedule_exist(
            boat_id = boat_id,
            location = location,
            arrived_date = arrived_date,
            ponton = ponton,
            leave_date = leave_date
        )
        
        if is_exist == False:
            
            await self.session.execute(
                insert(
                    
                    example_db.schedule
                    
                ).values(
                    
                    boat_id = boat_id,
                    location = location,
                    arrived_date = arrived_date,
                    ponton = ponton,
                    leave_date = leave_date
                )
            )
            
            await self.session.commit()
        
    async def _schedule_exist(self, 
        boat_id: int, 
        location: str, 
        arrived_date: datetime, 
        ponton: str, 
        leave_date: str
        ) -> bool:
        
        query_result = await self.session.execute( 
            select(
                exists().where(
                    and_(
                        example_db.schedule.boat_id == boat_id,
                        example_db.schedule.location == location,
                        example_db.schedule.arrived_date == arrived_date,
                        example_db.schedule.ponton == ponton,
                        example_db.schedule.leave_date == leave_date,
                    )
                )
            )
        )
        
        return query_result.scalar()
        