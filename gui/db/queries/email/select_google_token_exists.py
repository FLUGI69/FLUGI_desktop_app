from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.async_query_base.async_query_base import AsyncQueryBase

from db.tables import example_db

class select_google_token_exists(AsyncQueryBase):

    async def query(self, guid: str) -> example_db.google_token | None:

        query_result = await self.session.execute(
            select(
                
                example_db.user_device
                
            ).options(
                
                selectinload(example_db.user_device.tokens)
                
            ).where(
                
                example_db.user_device.guid == guid
            )
        )
        
        user_device = query_result.scalar_one_or_none()

        if user_device is not None:
            
            active_tokens = [token for token in user_device.tokens if token.is_active]
            
            if len(active_tokens) > 0:
                
                return active_tokens[0]

        return None