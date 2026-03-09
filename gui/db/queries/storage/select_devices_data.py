from sqlalchemy import select
from sqlalchemy.orm import selectinload

import typing as t 

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_devices_data(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.device]:
        
        query_result = (
            select(
                
                example_db.device
                
            ).options(
                
                selectinload(example_db.device.tenant)
            
            ).where(
                
                example_db.device.is_deleted == False
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()