from sqlalchemy.orm import aliased, joinedload, noload, with_loader_criteria
from sqlalchemy import select, func, and_
from sqlalchemy.engine import Row

from datetime import datetime
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from config import Config

class select_daily_tasks_from_boats(AsyncQueryBase):

    async def query(self) -> t.Sequence[Row[t.Tuple[example_db.boat, example_db.schedule]]]:
        
        now = datetime.now(Config.time.timezone_utc)
        
        schedule = aliased(example_db.schedule)
        
        earliest_schedule = (
            
            select(
                
                schedule.boat_id,
                func.min(schedule.leave_date).label("min_leave_date")
                
            ).where(
                and_(
                    schedule.arrived_date <= now,
                    schedule.leave_date >= now
                )
            ).group_by(
                
                schedule.boat_id
                
            ).subquery()
        )

        detailed_schedule = aliased(example_db.schedule)

        query_result = (
            select(
            
                example_db.boat,
                detailed_schedule
                
            ).join(
                
                detailed_schedule, 
                and_(
                    detailed_schedule.boat_id == example_db.boat.id,
                    detailed_schedule.arrived_date <= now,
                    detailed_schedule.leave_date >= now
                )
            ).join(
                
                earliest_schedule, 
                    and_(
                        earliest_schedule.c.boat_id == detailed_schedule.boat_id,
                        earliest_schedule.c.min_leave_date == detailed_schedule.leave_date
                    )
            ).options(
                
                joinedload(example_db.boat.works).options(
                    
                    noload(example_db.work.work_accessories),
                    noload(example_db.work.status),
                    noload(example_db.work.images)
                ),
                with_loader_criteria(
                    example_db.work,
                    example_db.work.finished_date.is_(None),
                    include_aliases = True
                )
            
            ).order_by(
                
                detailed_schedule.leave_date.asc()
            )
        )

        result = await self.session.execute(query_result)

        return result.unique().all()