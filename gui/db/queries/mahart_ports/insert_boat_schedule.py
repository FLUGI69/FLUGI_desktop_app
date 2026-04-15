from sqlalchemy import insert, select, update, exists, and_, or_, delete
from datetime import datetime
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_boat_schedule(AsyncQueryBase):

    async def query(self, 
        boat_id: int,
        schedules: t.List[dict]
        ):
        
        to_insert = []
        
        for schedule in schedules:
            
            is_exist = await self._schedule_exist(
                boat_id = boat_id,
                location = schedule["location"],
                arrived_date = schedule["arrived_date"],
                ponton = schedule["ponton"],
                leave_date = schedule["leave_date"]
            )
            
            if is_exist == True:
                continue
            
            overlapping = await self._get_overlapping_schedules(
                boat_id = boat_id,
                arrived_date = schedule["arrived_date"],
                leave_date = schedule["leave_date"]
            )
            
            if overlapping is not None and len(overlapping) > 0:
                
                first_id = overlapping[0].id
                
                await self.session.execute(
                    update(example_db.schedule).where(
                        example_db.schedule.id == first_id
                    ).values(
                        location = schedule["location"],
                        arrived_date = schedule["arrived_date"],
                        ponton = schedule["ponton"],
                        leave_date = schedule["leave_date"]
                    )
                )
                
                if len(overlapping) > 1:
                    
                    remaining_ids = [row.id for row in overlapping[1:]]
                    
                    await self.session.execute(
                        delete(
                            example_db.schedule
                        ).where(
                            example_db.schedule.id.in_(remaining_ids)
                        )
                    )
                
            else:
                
                to_insert.append({
                    "boat_id": boat_id,
                    "location": schedule["location"],
                    "arrived_date": schedule["arrived_date"],
                    "ponton": schedule["ponton"],
                    "leave_date": schedule["leave_date"]
                })
        
        if len(to_insert) > 0:
            
            await self.session.execute(
                insert(example_db.schedule),
                to_insert
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
    
    async def _get_overlapping_schedules(self,
        boat_id: int,
        arrived_date: datetime,
        leave_date: datetime
        ):
        
        query_result = await self.session.execute(
            select(example_db.schedule).where(
                and_(
                    example_db.schedule.boat_id == boat_id,
                    example_db.schedule.arrived_date <= leave_date,
                    example_db.schedule.leave_date >= arrived_date,
                )
            )
        )
        
        return query_result.scalars().all()
        