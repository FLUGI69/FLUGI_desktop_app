from sqlalchemy import select

import typing as t 

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_material_data(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.material]:
        
        query_result = (
            select(
                
                example_db.material
                
            ).where(
                
                example_db.material.is_deleted == False
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()
        
        
        