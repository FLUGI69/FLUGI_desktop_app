from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.engine import Row

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_existing_other_work_prices_hun(AsyncQueryBase):

    async def query(self) -> Row[t.Tuple[example_db.other_work_prices_hun]] | None:
        
        query_result = (
            select(
                
                example_db.other_work_prices_hun
            
            ).options(
                
                selectinload(example_db.other_work_prices_hun.tiers)
            )
        )

        result = await self.session.execute(query_result)
        
        return result.first()
