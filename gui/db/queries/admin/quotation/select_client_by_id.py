from sqlalchemy import select

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_client_by_id(AsyncQueryBase):

    async def query(self, client_id: int) -> t.Optional[example_db.client]:
    
        query_result = (
            select(
                
                example_db.client
                
            ).where(
                
                example_db.client.id == client_id
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().first()
