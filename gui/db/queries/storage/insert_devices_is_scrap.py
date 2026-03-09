from sqlalchemy import insert, update, and_
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_devices_is_scrap(AsyncQueryBase):
    # Scrap device is deducted from stock and inserted as a new item with is_scrap flag,
    # quantity = scrap amount.

    async def query(self, 
        storage_id: int,
        name: str, 
        manufacture_number: str, 
        quantity: float, 
        manufacture_date: datetime, 
        price: float,
        commissioning_date: datetime,
        purchase_source: str,
        purchase_date: datetime, 
        inspection_date: datetime,
        is_deleted: bool,
        deleted_date: datetime,
        is_scrap: bool,
        previous_quantity: float,
        uuid: bytes
        ) -> None:

        quantity_to_remove = quantity
        
        scrap_quantity = previous_quantity - quantity_to_remove
        
        if quantity_to_remove < 0 or scrap_quantity < 0:
            
            raise ValueError("Invalid quantities - quantity_to_remove: %s, scrap: %s" % (
                quantity_to_remove, 
                scrap_quantity
                )
            )
        
        await self.update_remaining_devices_reference_quantity(
            quantity = quantity_to_remove,
            storage_id = storage_id,
            manufacture_number = manufacture_number,
            inspection_date = inspection_date
        )
        
        await self.session.execute(
            insert(
                
                example_db.device
                
            ).values(
                
                storage_id = storage_id,
                name = name,
                manufacture_number = manufacture_number,
                quantity = scrap_quantity,
                manufacture_date = manufacture_date,
                price = price,
                commissioning_date = commissioning_date,
                purchase_source = purchase_source,
                purchase_date = purchase_date,
                inspection_date = inspection_date,
                is_scrap = is_scrap,
                is_deleted = is_deleted,
                deleted_date = deleted_date,
                uuid = uuid
            )
        )
        
        await self.session.commit()
        
    async def update_remaining_devices_reference_quantity(self, 
        quantity: float,
        storage_id: int,
        manufacture_number: str,
        inspection_date: datetime
        ):
        
        await self.session.execute(
            update(
                
                example_db.device
                
            ).where(
                
                and_(
                    
                    example_db.device.storage_id == storage_id,
                    example_db.device.manufacture_number == manufacture_number
                )
                
            ).values(
                
                quantity = quantity,
                inspection_date = inspection_date
            )
        )
        
        await self.session.commit()
        