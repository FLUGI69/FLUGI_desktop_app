from sqlalchemy import update, select
from datetime import datetime
import logging
from decimal import Decimal

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.logger import LoggerMixin

class update_returnable_data(AsyncQueryBase, LoggerMixin):

    log: logging.Logger
    
    async def query(self, 
        id: int,
        storage_id: int | None = None,
        name: str | None = None,
        quantity: float | None = None,
        manufacture_number: str | None = None,
        manufacture_date: datetime | None = None,
        price: float | None = None,
        inspection_date: datetime | None = None,
        purchase_source: str | None = None,
        purchase_date: datetime | None = None
        ):
        
        values_to_update = {}
        
        current_row = await self.select_current_row_by_id(id)
        
        if current_row.quantity == Decimal("0.0000"):
            
            values_to_update["is_returned"] = False

        if price is not None:
            
            values_to_update['price'] = price
        
        if storage_id is not None:
            
            values_to_update['storage_id'] = storage_id
        
        if name is not None:
            
            values_to_update['name'] = name
            
        if quantity is not None:
            
            values_to_update['quantity'] = quantity
            
        if manufacture_number is not None:
            
            values_to_update['manufacture_number'] = manufacture_number
            
        if manufacture_date is not None:
            
            values_to_update['manufacture_date'] = manufacture_date
            
        if inspection_date is not None:
            
            values_to_update['inspection_date'] = inspection_date
            
        if purchase_source is not None:
            
            values_to_update["purchase_source"] = purchase_source
            
        if purchase_date is not None:
            
            values_to_update['purchase_date'] = purchase_date
            
        if not values_to_update:
            return

        self.log.debug("Values to update: %s" % values_to_update)
        
        query_result = (
            update(
                
                example_db.returnable_packaging
                
            ).where(
                
                example_db.returnable_packaging.id == id
                
            ).values(
                
                **values_to_update
            )
        )

        await self.session.execute(query_result)
        
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