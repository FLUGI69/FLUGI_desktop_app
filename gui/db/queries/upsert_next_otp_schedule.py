from sqlalchemy import insert, select, update, exists, and_, or_, delete
from datetime import datetime, timedelta

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from config import Config

class upsert_next_otp_schedule(AsyncQueryBase):

    async def query(self) -> tuple[datetime, bool]:
        
        now = datetime.now(Config.time.timezone_utc)
        
        # scheduled_at = now + timedelta(seconds = 30)
        # scheduled_at = scheduled_at.replace(microsecond = 0)
        
        if now.month == 12:
            
            scheduled_at = now.replace(
                year = now.year + 1,
                month = 1,
                day = 3,
                hour = 0,
                minute = 0,
                second = 0,
                microsecond = 0
            )
            
        else:
            
            scheduled_at = now.replace(
                month = now.month + 1,
                day = 3,
                hour = 0,
                minute = 0,
                second = 0,
                microsecond = 0
            )
        
        async with self.session.begin():    
             
            last_scheduled_at, executed = await self.select_last_schedule_time()
            
            if executed == False:
            
                if last_scheduled_at is None:
                    
                    await self.insert_new_schedule(
                        scheduled_at = scheduled_at,
                        executed = executed,
                        execution_time = None
                    )
                    
                    return scheduled_at, True
                
                elif last_scheduled_at <= now:
                    
                    scheduled_at = await self.update_execution_time(
                        scheduled_at = scheduled_at,
                        last_scheduled_at = last_scheduled_at,
                        executed = True,
                        execution_time = now
                    )

                    return scheduled_at, True
                    
                else:
                    
                    return last_scheduled_at, False
            
            else:
                
                await self.insert_new_schedule(
                    scheduled_at = scheduled_at,
                    executed = False,
                    execution_time = None
                )
                
                return scheduled_at, True

    async def update_execution_time(self, 
        scheduled_at: datetime,
        last_scheduled_at: datetime,
        executed: bool,
        execution_time: datetime
        ) -> datetime:
        
        await self.session.execute(
            update(
                example_db.otp_schedule
            ).where(
                and_(
                    example_db.otp_schedule.scheduled_at == last_scheduled_at,
                    example_db.otp_schedule.executed == False
                )
            ).values(
                executed = executed,
                executed_at = execution_time
            )
        )
        
        await self.insert_new_schedule(
            scheduled_at = scheduled_at,
            executed = False,
            execution_time = None
        )
        
        return scheduled_at
    
    async def insert_new_schedule(self, 
        scheduled_at: datetime, 
        executed: bool, 
        execution_time: datetime
        ) -> None:
        
        await self.session.execute(
            insert(
                example_db.otp_schedule
            ).values(
                scheduled_at = scheduled_at,
                executed = executed,
                executed_at = execution_time
            )
        )
        
    async def select_last_schedule_time(self) -> tuple[datetime, bool]:
        
        result = await self.session.execute(
            select(
                example_db.otp_schedule.scheduled_at,
                example_db.otp_schedule.executed
            ).order_by(
                example_db.otp_schedule.scheduled_at.desc()
            ).limit(1).with_for_update()
        )
        
        row = result.first()
        
        if row is None:
            
            return None, False
        
        scheduled_at: datetime = row.scheduled_at

        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo = Config.time.timezone_utc)

        return scheduled_at, row.executed