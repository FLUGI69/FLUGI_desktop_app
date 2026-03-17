from sqlalchemy import select, func

from datetime import date

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_next_order_number_preview(AsyncQueryBase):
    
    async def query(self) -> str:
        
        year = date.today().strftime("%Y")
        
        count_result = await self.session.execute(
            select(func.count()).select_from(
                
                example_db.order_number
            
            ).where(
                
                example_db.order_number.order_number.like(f"{year}%")
            )
        )
        
        count = count_result.scalar()
        
        return f"{year}{count + 1:04d}"
