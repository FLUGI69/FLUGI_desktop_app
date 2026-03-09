from sqlalchemy import select
from sqlalchemy.orm import selectinload, with_loader_criteria
from datetime import datetime 
from sqlalchemy.engine import Row

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_existing_other_work_prices(AsyncQueryBase):

    async def query(self) -> Row[t.Tuple[example_db.other_work_prices]]:
        

        query_result = (
            select(
                
                example_db.other_work_prices
            )
        )

        result = await self.session.execute(query_result)
        
        return result.one()
 