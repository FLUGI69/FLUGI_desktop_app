from datetime import datetime
from sqlalchemy import insert, update

from decimal import Decimal
from pathlib import Path
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.dc.material import MaterialData
from exceptions import ImageNotFound

class insert_work_by_boat_id(AsyncQueryBase):

    async def query(self, 
        boat_id: int, 
        leader: str,
        order_date: datetime,
        description: str,
        is_contractor: bool,
        img_paths: list = [],
        materials: t.List[MaterialData] = []
        ):
    
        async with self.session.begin():
            
            new_work = example_db.work(
                boat_id = boat_id,
                leader = leader,
                order_date = order_date,
                description = description,
                start_date = None,
                finished_date = None,
                transfered = None,
                is_contractor = True if is_contractor is True else False
            )
            
            self.session.add(new_work)
            
            await self.session.flush()
            
            work_id = new_work.id
            
            if img_paths != []:
                
                for path in img_paths:
                    
                    file_path = Path(path)
                    
                    if file_path.exists() == False:
                        
                        raise ImageNotFound(file_path)
                    
                    else:
                    
                        with open(file_path, "rb") as f:
                            
                            file_data = f.read()
                            
                            await self.handle_and_insert_img_data(
                                file_data = file_data,
                                work_id = work_id
                            )
            
            if materials != []:
                
                await self.insert_work_materials(work_id = work_id, materials = materials)
            
    async def handle_and_insert_img_data(self, file_data: bytes, work_id: int):
        
        await self.session.execute(
            insert(
                
                example_db.work_img
                
            ).values(
                
                work_id = work_id,
                img = file_data
            )
        )
        
    async def insert_work_materials(self, work_id: int, materials: t.List[MaterialData]):
        
        for m in materials:
            
            await self.update_material_quantity(m)
        
        values_to_insert = [{
            "work_id": work_id, 
            "component_id": material.id, 
            "quantity": material.quantity
            } for material in materials]
        
        await self.session.execute(
            insert(
                
                example_db.work_accessories
                
            ).values(
                
                values_to_insert
            )
        )
        
    async def update_material_quantity(self, material: MaterialData):
        
        quantity = Decimal(str(material.quantity))
        
        await self.session.execute(
            update(
                
                example_db.material
                
            ).where(
                
                example_db.material.id == material.id
                
            ).values(
                
                quantity = example_db.material.quantity - quantity
            )
        )