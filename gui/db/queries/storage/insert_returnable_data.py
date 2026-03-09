from sqlalchemy import insert
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_returnable_data(AsyncQueryBase):

    async def query(self, 
        storage_id: int, 
        name: str,
        manufacture_number: str, 
        quantity: float,
        manufacture_date: datetime,
        price: float,
        purchase_source: str,
        purchase_date: datetime,
        inspection_date: datetime,
        returned_date: datetime,
        is_returned: bool,
        is_deleted: bool,
        deleted_date: datetime,
        uuid: bytes
        ) -> None:
    
        await self.session.execute(
            insert(
                
                example_db.returnable_packaging
                
            ).values(
                
                storage_id = storage_id,
                name = name,
                manufacture_number = manufacture_number,
                quantity = quantity,
                manufacture_date = manufacture_date,
                price = price,
                purchase_source = purchase_source,
                purchase_date = purchase_date,
                inspection_date = inspection_date,
                returned_date = returned_date,
                is_returned = is_returned,
                is_deleted = is_deleted,
                deleted_date = deleted_date,
                uuid = uuid
            )
        )
        
        await self.session.commit()
        
        