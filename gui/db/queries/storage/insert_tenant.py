from sqlalchemy import insert, update
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase 
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from db.tables import example_db

class insert_tenant(AsyncQueryBase):

    async def query(self, 
        item_id: int,
        item_name: str,
        item_type: StorageItemTypeEnum,
        item_quantity: float, 
        tenant_quantity: float,
        tenant_name: str,
        rental_start: datetime,
        rental_end: datetime | None,
        rental_price: float,
        is_daily_price: bool
        ) -> None:
        
        async with self.session.begin():
            
            formatted_price = f"{rental_price:,.2f}".replace(",", ".")
      
            if item_type == StorageItemTypeEnum.TOOL:
                
                await self.update_tools_quantity_by_id(
                    id = item_id,
                    tools_quantity = item_quantity,
                    tenant_quantity = tenant_quantity
                )

                note = "Rental period expired for %s. Rented tool: %s (ID: %s). \
                    Rental period cost: %s HUF" % (
                        tenant_name,
                        item_name,
                        str(item_id),
                        formatted_price
                    )
            
            if item_type == StorageItemTypeEnum.DEVICE:
                
                await self.update_device_quantity_by_id(
                    id = item_id,
                    devices_quantity = item_quantity,
                    tenant_quantity = tenant_quantity
                )
                
                note = "Rental period expired for %s. Rented device: %s (ID: %s). \
                    Rental period cost: %s HUF" % (
                        tenant_name,
                        item_name,
                        str(item_id),
                        formatted_price
                    )
                
            result = await self.session.execute(
                insert(
                    
                    example_db.tenant
                    
                ).values(
                    
                    item_id = item_id,
                    item_type = item_type,
                    tenant_name = tenant_name,
                    rental_start = rental_start,
                    rental_end = rental_end,
                    returned = False,
                    rental_price = rental_price,
                    quantity = tenant_quantity,
                    is_daily_price = is_daily_price
                )
            )
            
            tenant_id = result.lastrowid
            
            await self.insert_rental_history(
                tenant_id = tenant_id,
                is_paid = False
            )
            
            if rental_end is not None:
            
                calendar_id = await self.insert_tenant_reminder(
                    note = note,
                    reminder_date = rental_end,
                    used = False
                )
                
                await self.insert_tenant_calendar(
                    tenant_id = tenant_id,
                    calendar_id = calendar_id
                )
    
    async def update_device_quantity_by_id(self,
        id: int,
        devices_quantity: float,
        tenant_quantity: float
        ):
        
        await self.session.execute(
            update(
                
                example_db.device
                
            ).where(
                
                example_db.device.id == id
                
            ).values(
                
                quantity = devices_quantity - tenant_quantity
            )
        )
        
    async def update_tools_quantity_by_id(self,
        id: int, 
        tools_quantity: float, 
        tenant_quantity: float
        ):
        
        await self.session.execute(
            update(
                
                example_db.tool
                
            ).where(
                
                example_db.tool.id == id
                
            ).values(
                
                quantity = tools_quantity - tenant_quantity
            )
        )
        
    # Insert reminder for tenant's rental end date    
    async def insert_tenant_reminder(self, 
        note: str,
        reminder_date: datetime, 
        used: bool
        ):
        
        result = await self.session.execute(
            insert(
                
                example_db.calendar
                
            ).values(
                
                note = note,
                reminder_date = reminder_date,
                used = used
            )
        )
        
        return result.lastrowid
        
    async def insert_rental_history(self,
        tenant_id: int,
        is_paid: bool
        ):
        
        await self.session.execute(
            insert(
                
                example_db.rental_history
                
            ).values(
                
                tenant_id = tenant_id,
                is_paid = is_paid
            )
        )
        
    async def insert_tenant_calendar(self, tenant_id: int, calendar_id: int) -> None:
        
        await self.session.execute(
            insert(
                
                example_db.tenant_reminder
                
            ).values(
                
                tenant_id = tenant_id,
                calendar_id = calendar_id
            )
        )
