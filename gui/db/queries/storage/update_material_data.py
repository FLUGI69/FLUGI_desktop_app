from sqlalchemy import update
import logging
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.logger import LoggerMixin

class update_material_data(AsyncQueryBase, LoggerMixin):
    
    log: logging.Logger

    async def query(self, 
        id: int,
        inspection_date: datetime,
        storage_id: int | None = None,
        name: str | None = None,
        manufacture_number: str | None = None,
        quantity: float | None = None,
        unit: str | None = None,
        manufacture_date: datetime | None = None,
        price: float | None = None,
        purchase_source: str | None = None,
        purchase_date: datetime | None = None
        ):
        
        values_to_update = {}
        
        values_to_update['inspection_date'] = inspection_date
        
        if storage_id is not None:
            
            values_to_update['storage_id'] = storage_id
            
        if manufacture_number is not None:
            
            values_to_update['manufacture_number'] = manufacture_number
            
        if manufacture_date is not None:
            
            values_to_update['manufacture_date'] = manufacture_date
        
        if purchase_source is not None:
            
            values_to_update['purchase_source'] = purchase_source
        
        if name is not None:
            
            values_to_update['name'] = name
            
        if quantity is not None:
            
            values_to_update['quantity'] = quantity
            
        if unit is not None:
            
            values_to_update['unit'] = unit
            
        if price is not None:
            
            values_to_update['price'] = price
            
        if purchase_date is not None:
            
            values_to_update['purchase_date'] = purchase_date
            
        if not values_to_update:
            return

        self.log.debug("Values to update: %s" % values_to_update)
        
        query_result = (
            update(
                
                example_db.material
                
            ).where(
                
                example_db.material.id == id
                
            ).values(
                
                **values_to_update
            )
        )

        await self.session.execute(query_result)
        
        await self.session.commit()