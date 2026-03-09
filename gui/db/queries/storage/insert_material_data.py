from sqlalchemy import insert
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class insert_material_data(AsyncQueryBase):

    async def query(self, 
        storage_id: int, 
        name: str,
        manufacture_number: str, 
        quantity: float, 
        unit: str, 
        manufacture_date: datetime,
        price: float,
        purchase_source: str,
        purchase_date: datetime,
        inspection_date: datetime,
        is_deleted: bool,
        deleted_date: datetime,
        uuid: bytes
        ) -> None:
    
        await self.session.execute(
            insert(
                
                example_db.material
                
            ).values(
                
                storage_id = storage_id,
                name = name,
                manufacture_number = manufacture_number,
                quantity = quantity,
                unit = unit,
                manufacture_date = manufacture_date,
                price = price,
                purchase_source = purchase_source,
                purchase_date = purchase_date,
                inspection_date = inspection_date,
                is_deleted = is_deleted,
                deleted_date = deleted_date,
                uuid = uuid
            )
        )
        
        await self.session.commit()
        
        