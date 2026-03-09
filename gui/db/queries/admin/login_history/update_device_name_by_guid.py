from sqlalchemy import update, and_

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_device_name_by_guid(AsyncQueryBase):

    async def query(self, guid: str, name: str) -> None:
        
        query_result = (
            update(
                
                example_db.user_device
                
            ).where(
                
                example_db.user_device.guid == guid,

            ).values(
                
                username = name
            )
        )

        await self.session.execute(query_result)
        
        await self.session.commit()