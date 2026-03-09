from sqlalchemy import select

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_current_device_by_guid(AsyncQueryBase):

    async def query(self, guid: str) -> example_db.user_device | None:
        
        query_result = (
            select(
                
                example_db.user_device
                
            ).where(
                
                example_db.user_device.guid == guid
            )
        )

        result = await self.session.execute(query_result)
        
        return result.scalar_one_or_none()
        