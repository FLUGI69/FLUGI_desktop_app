from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_all_rental_history(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.rental_history]:
    
        query_result = (
            select(
                
                example_db.rental_history
                
            ).options(
                
                selectinload(
                    
                    example_db.rental_history.tenant
                    
                ).options(
                    
                    selectinload(example_db.tenant.tool),
                    selectinload(example_db.tenant.device)
                )
            )
        )

        result = await self.session.execute(query_result)

        query_sequence = result.scalars().all()

        query_sequence.sort(key = lambda rental_history: rental_history.tenant.rental_end or datetime.max)
        
        return query_sequence