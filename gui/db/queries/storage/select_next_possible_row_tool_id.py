from sqlalchemy import select, desc

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_next_possible_row_tool_id(AsyncQueryBase):

    async def query(self) -> int:
        
        query_result = await self.session.execute(
            select(
                
                example_db.tool.id
                
            ).order_by(
                
                desc(example_db.tool.id)
                
            ).limit(1)
        )

        result = query_result.scalars().first()
        
        if result is None:
            
            return 1
        
        else:
            
            return result + 1