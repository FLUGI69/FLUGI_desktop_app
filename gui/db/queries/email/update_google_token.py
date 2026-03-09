from sqlalchemy import update, and_
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_google_token_by_guid(AsyncQueryBase):

    async def query(self, guid: str, token: str, expiry: datetime) -> None:
        
        query_result = (
            update(
                
                example_db.google_token
                
            ).where(
                
                and_(
                    example_db.google_token.user_device.has(guid = guid),
                    example_db.google_token.is_active == True
                )
                
            ).values(
                
                token = token,
                expiry = expiry
            )
        )

        await self.session.execute(query_result)
        
        await self.session.commit()