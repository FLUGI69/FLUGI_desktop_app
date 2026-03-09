from sqlalchemy import update, and_
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.enums.storage_item_type_enum import StorageItemTypeEnum

class update_rental_history_by_tenant_id(AsyncQueryBase):

    async def query(self, 
        tenant_id: int,
        item_type: StorageItemTypeEnum, 
        item_id: int,
        current_is_paid: bool,
        current_returned: bool,
        current_rental_start: datetime,
        current_rental_end: datetime,
        current_amount: float,
        rented_quantity: float,
        new_is_paid: bool = None, 
        new_returned: bool = None
        ):
        
        async with self.session.begin():
            
            if new_is_paid is not None:
        
                await self.update_rental_history(
                    tenant_id = tenant_id, 
                    item_type = item_type,
                    item_id = item_id,
                    current_is_paid = current_is_paid,
                    current_returned = current_returned,
                    current_rental_start = current_rental_start,
                    current_rental_end = current_rental_end,
                    current_amount = current_amount,
                    new_is_paid = new_is_paid
                )
            
            if new_returned is not None:
                
                await self.update_tenan(
                    tenant_id = tenant_id, 
                    item_type = item_type,
                    item_id = item_id,
                    current_returned = current_returned,
                    current_rental_start = current_rental_start,
                    current_rental_end = current_rental_end,
                    new_returned = new_returned,
                    rented_quantity = rented_quantity
                )    

    async def update_rental_history(self,
        tenant_id: int, 
        item_type: StorageItemTypeEnum,
        item_id: int,
        current_is_paid: bool,
        current_returned: bool,
        current_rental_start: datetime,
        current_rental_end: datetime,
        current_amount: float,
        new_is_paid: bool
        ):
        
        await self.session.execute(
            update(
                
                example_db.rental_history
                
            ).where(
                and_(
                    
                    example_db.rental_history.tenant_id == tenant_id,
                    example_db.rental_history.is_paid == current_is_paid,
                    
                    example_db.rental_history.tenant.has(
                        and_(
                            example_db.tenant.item_type == item_type,
                            example_db.tenant.item_id == item_id,
                            example_db.tenant.rental_price == current_amount,
                            example_db.tenant.rental_start == current_rental_start,
                            example_db.tenant.rental_end == current_rental_end,
                            example_db.tenant.returned == current_returned
                        )
                    )
                )
            ).values(
                
                is_paid = new_is_paid
            )
        )
    
    async def update_tenan(self,
        tenant_id: int,
        item_type: StorageItemTypeEnum, 
        item_id: int,
        current_returned: bool,
        current_rental_start: datetime,
        current_rental_end: datetime,
        new_returned: bool,
        rented_quantity: float
        ):
        
        await self.update_item_quantity(        
            item_id = item_id,
            item_type = item_type,
            quantity = rented_quantity
        )

        await self.session.execute(
            update(
                
                example_db.tenant
                
            ).where(
                and_(
                    example_db.tenant.id == tenant_id,
                    example_db.tenant.item_type == item_type,
                    example_db.tenant.item_id == item_id,
                    example_db.tenant.rental_start == current_rental_start,
                    example_db.tenant.rental_end == current_rental_end,
                    example_db.tenant.returned == current_returned
                )
            ).values(
                
                returned = new_returned
            )
        )
        
    async def update_item_quantity(self,
        item_id: int,
        item_type: StorageItemTypeEnum,
        quantity: float,
        ):

        if item_type == StorageItemTypeEnum.DEVICE:
            
            await self.session.execute(
                update(
                    
                    example_db.device
                    
                ).where(
                    
                    example_db.device.id == item_id
                    
                ).values(
                    
                    quantity = quantity
                )
            )
            
        elif item_type == StorageItemTypeEnum.TOOL:
            
            await self.session.execute(
                update(
                    
                    example_db.tool
                    
                ).where(
                    
                    example_db.tool.id == item_id
                    
                ).values(
                    
                    quantity = quantity
                )
            )
        
        else: 
            
            self.log.error("Unknown item type update item quantity failed")