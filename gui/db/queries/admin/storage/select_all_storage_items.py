from sqlalchemy import select
from sqlalchemy.orm import selectinload

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_all_storage_items(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.storage]:
        
        query_result = (
            select(
                
                example_db.storage
                
            ).options(
                
                selectinload(example_db.storage.materials),
                selectinload(example_db.storage.tools).selectinload(example_db.tool.tenant),
                selectinload(example_db.storage.devices).selectinload(example_db.device.tenant),
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalars().all()
        