from sqlalchemy import update
from decimal import Decimal

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_other_work_prices(AsyncQueryBase):

    async def query(self,
        work_during_hours: Decimal,
        work_outside_hours: Decimal,
        work_sundays: Decimal,
        travel_budapest: Decimal,
        travel_outside: Decimal,
        travel_time: Decimal,
        travel_time_outside: Decimal,
        travel_time_sundays: Decimal,
        accommodation: Decimal
        ):
        
        query_result = (
            update(
                
                example_db.other_work_prices
                
            ).values(
                
                work_during_hours = work_during_hours,
                work_outside_hours = work_outside_hours,
                work_sundays = work_sundays,
                travel_budapest = travel_budapest,
                travel_outside = travel_outside,
                travel_time = travel_time,
                travel_time_outside = travel_time_outside,
                travel_time_sundays = travel_time_sundays,
                accommodation = accommodation
            )
        )

        await self.session.execute(query_result)
        await self.session.commit()
