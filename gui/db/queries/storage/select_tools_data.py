from sqlalchemy import select
from sqlalchemy.orm import selectinload

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_tools_data(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.tool]:
        
        query_result = (
            select(
                
                example_db.tool
                
            ).options(
                
                selectinload(example_db.tool.tenant)
                
            ).where(
                
                example_db.tool.is_deleted == False
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()