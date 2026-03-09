from sqlalchemy import insert
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_storage_data(AsyncQueryBase):

    async def query(self, name: str, location: str) -> None:
    
        await self.session.execute(
            insert(
                
                example_db.storage
                
            ).values(
                
                name = name,
                location = location
            )
        )
        
        await self.session.commit()
        
        