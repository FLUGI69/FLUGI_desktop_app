from sqlalchemy import update, insert, select
from datetime import datetime
import logging
from decimal import Decimal

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.logger import LoggerMixin
from config import Config

class update_returnable_packaging_returned_by_id(AsyncQueryBase, LoggerMixin):

    log: logging.Logger
    
    async def query(self, 
        id: int,
        quantity: float
        ):

        quantity = Decimal(str(quantity))
      
        current_row = await self.select_current_row_by_id(id)
        
        if current_row is not None:
            
            remaining_quantity = current_row.quantity - quantity
            
            await self.insert_returned_packaging_history(
                id = current_row.id,
                quantity = quantity
            )
        
            query_result = (
                update(
                    
                    example_db.returnable_packaging
                    
                ).where(
                    
                    example_db.returnable_packaging.id == current_row.id
                    
                ).values(
                    quantity = remaining_quantity,
                    inspection_date = datetime.now(Config.time.timezone_utc),
                    returned_date = datetime.now(Config.time.timezone_utc),
                    is_returned = False if remaining_quantity > Decimal("0.0000") else True
                )
            )

            await self.session.execute(query_result)
            
            await self.session.commit()
        
    async def insert_returned_packaging_history(self,
        id: int,
        quantity: float
        ):
        
        await self.session.execute(
            insert(
                
                example_db.returned_packaging_history
                
            ).values(
                
                returnable_packaging_id = id,
                quantity = quantity,
                returned_date = datetime.now(Config.time.timezone_utc)
            )
        )
        
        await self.session.commit()
        
    async def select_current_row_by_id(self,
        id: int
        ) -> example_db.returnable_packaging:

        query_results = await self.session.execute(
            select(
                
                example_db.returnable_packaging
                
            ).where(
                
                example_db.returnable_packaging.id == id
            )
        )
        
        return query_results.scalar_one_or_none()