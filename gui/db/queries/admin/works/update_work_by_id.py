from sqlalchemy import select, update, exists, insert, delete, and_
from datetime import datetime
import typing as t
import aiofiles
from decimal import Decimal

from PyQt6.QtCore import QDateTime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.dc.admin.work.status_note import AdminWorkStatusNote
from utils.dc.material import MaterialData

class update_work_by_id(AsyncQueryBase):
     
    async def query(self, 
        work_id: int,
        leader: str | None,
        order_date: datetime | None,
        description: str | None,
        prev_transfered: bool,
        transfered: bool,
        is_contractor: bool | None,
        start_date: datetime | None,
        finished_date: datetime | None,
        new_note: str | None,
        new_imgs: t.List[str],
        work_accessories: t.List[MaterialData] = [], 
        deleted_work_material: t.List[MaterialData] = [],
        available_materials: t.List[MaterialData] = [],
        deleted_available_material: t.List[MaterialData] = [],
        changed_notes: t.List[AdminWorkStatusNote] = [],
        deleted_img_bytes: dict = {}
        ):

        async with self.session.begin():
            
            current_work_component_ids = await self.select_current_work_component_ids(work_id)
            
            await self.update_work_by_id(
                id = work_id,
                leader = leader,
                order_date = order_date,
                description = description,
                prev_transfered = prev_transfered,
                transfered = transfered,
                is_contractor = is_contractor,
                start_date = start_date,
                finished_date = finished_date,
            )
            
            if len(new_imgs) > 0:

                for img in new_imgs:
                    
                    async with aiofiles.open(img, 'rb') as f:
                        
                        file_bytes = await f.read()
                        
                        self.session.add(example_db.work_img(
                            work_id = work_id,
                            img = file_bytes
                            )
                        )
            
            works_status_is_exist = await self.work_status_is_exist(work_id)
                   
            if prev_transfered == False and transfered == True:
                
                if works_status_is_exist == False:
                    
                    await self.insert_work_status(work_id)
                
            else:
                
                if new_note is not None and works_status_is_exist == True:
                    
                    await self.insert_work_status_notes(
                        work_id = work_id,
                        new_note = new_note
                    )
                    
            if len(deleted_img_bytes) > 0:
                
                img_ids = list(deleted_img_bytes.keys())
                    
                await self.remove_work_img_by_img_id(
                    work_id = work_id,
                    img_ids = img_ids
                )

            if len(changed_notes) > 0:
                
                for note in changed_notes:
                    
                    await self.update_note_by_id(
                        id = note.id,
                        note = note.note
                    )
            
            await self.handle_material_changes(
                work_id = work_id,
                current_work_component_ids = current_work_component_ids,
                work_accessories = work_accessories, 
                deleted_work_material = deleted_work_material,
                available_materials = available_materials,
                deleted_available_material = deleted_available_material
            )
          
    async def update_work_by_id(self,
        id: int,
        leader: str | None,
        order_date: datetime | None,
        description: str | None,
        prev_transfered: bool,
        transfered: bool,
        is_contractor: bool | None,
        start_date: datetime | None,
        finished_date: datetime | None,
        ):
        
        values_to_update = {}
        
        if leader is not None:
            
            values_to_update["leader"] = leader
            
        if order_date is not None:
            
            values_to_update["order_date"] = order_date    
            
        if description is not None:
            
            values_to_update["description"] = description
            
        if prev_transfered is False:
            
            values_to_update["transfered"] = transfered
            
        if is_contractor is not None:
            
            values_to_update["is_contractor"] = is_contractor
            
        if start_date is not None:
            
            values_to_update["start_date"] = start_date
            
        if finished_date is not None:
            
            values_to_update["finished_date"] = finished_date
        
        self.log.debug("Values to update for work table: %s" % values_to_update)
        
        await self.session.execute(
            update(
                
                example_db.work
                
            ).where(
                
                example_db.work.id == id
                
            ).values(
                
                **values_to_update
            )
        )

    async def work_status_is_exist(self,
        work_id: int
        ) -> bool:
        
        query_result = await self.session.execute(
            select(
                exists().where(
                    
                    example_db.work_status.work_id == work_id
                )
            )
        )
        
        result = query_result.scalar()
        
        if result is not None:
            
            return result
        
        return False

    async def insert_work_status(self,
        work_id: int
        ):

        await self.session.execute(
            insert(
                
                example_db.work_status
                
            ).values(
                
                work_id = work_id,
                delivered_back = False
            )
        )

    async def select_current_work_status_id_by_work_id(self,
        work_id: int
        ) -> int:
        
        query_result = await self.session.execute(
            select(
                
                example_db.work_status.id
                
            ).where(
                
                example_db.work_status.work_id == work_id
            )
        )

        return query_result.scalar_one()

    async def insert_work_status_notes(self,
        work_id: int,
        new_note: str
        ):
        
        work_status_id = await self.select_current_work_status_id_by_work_id(work_id)
        
        await self.session.execute(
            insert(
                
                example_db.work_status_note
                
            ).values(
                
                work_status_id = work_status_id,
                note = new_note
            )
        )
        
    async def remove_work_img_by_img_id(self,
        work_id: int,
        img_ids: list
        ):
        
        await self.session.execute(
            delete(
                
                example_db.work_img
                
            ).where(
                and_(
                    example_db.work_img.work_id == work_id,
                    example_db.work_img.id.in_(img_ids)
                )
            )
        )

    async def update_note_by_id(self,
        id: int,
        note: str
        ):
        
        await self.session.execute(
            update(
                
                example_db.work_status_note
            
            ).where(
            
                example_db.work_status_note.id == id
                
            ).values(
                
                note = note
            )
        )
    
    async def handle_material_changes(self,
        work_id: int,
        current_work_component_ids: t.List[int],
        work_accessories: t.List[MaterialData] = [], 
        deleted_work_material: t.List[MaterialData] = [],
        available_materials: t.List[MaterialData] = [],
        deleted_available_material: t.List[MaterialData] = [],
        ):
        
        if len(work_accessories) > 0:
            
            deleted_ids = {deleted.id for deleted in deleted_available_material}
            
            for material in work_accessories:

                if material.id in deleted_ids:
                    continue
                
                if material.id in current_work_component_ids:
                    
                    await self.update_work_accessorie_quantity_by_id(
                        work_id = work_id,
                        material = material
                    )
                
                else:
                    
                    await self.insert_work_accessorie(                        
                        work_id = work_id,
                        material = material
                    )

        if len(deleted_work_material) > 0:
            
            for material in deleted_work_material:
                
                await self.update_available_quantity_by_removed_work_accessorie(
                    quantity = material.quantity,
                    id = material.id
                )
                
        if len(available_materials) > 0:
            
            deleted_ids = {deleted.id for deleted in deleted_work_material}
            
            for available_material in available_materials:

                if available_material.id in deleted_ids:
                    continue
                
                await self.update_available_quantity_by_id(
                    id = available_material.id,
                    quantity = available_material.quantity
                )
                
        if len(deleted_available_material) > 0:
            
            deleted_component_ids = []
            
            for material in deleted_available_material:
                
                await self.update_available_quantity_by_substraction(
                    work_id = work_id,
                    material = material,
                    current_work_component_ids = current_work_component_ids
                )
                
                deleted_component_ids.append(material.id)

            await self.delete_work_accessorie_by_id(
                work_id = work_id,
                component_ids = deleted_component_ids
            )
            
    async def update_available_quantity_by_substraction(self,
        work_id: int,
        material: MaterialData,
        current_work_component_ids: t.List[int]
        ):
    
        values_to_substract = Decimal(str(material.quantity))
        
        await self.session.execute(
            update(
                
                example_db.material
                
            ).where(
                
                example_db.material.id == material.id
                
            ).values(
                
                quantity = example_db.material.quantity - values_to_substract
            )
        )
        
        if material.id in current_work_component_ids:
            
            await self.update_work_accessorie_by_substraction(
                work_id = work_id,
                component_id = material.id,
                quantity = material.quantity
            )
        
        else:
            
            await self.insert_work_accessorie(
                work_id = work_id,
                material = material
            )
    
    async def update_work_accessorie_by_substraction(self,
        work_id: int,
        component_id: int,
        quantity: float
        ):
        
        values_to_substract = Decimal(str(quantity))
        
        await self.session.execute(
            update(
                
                example_db.work_accessories
            
            ).where(
                and_(
                    example_db.work_accessories.work_id == work_id,
                    example_db.work_accessories.component_id == component_id
                )
            ).values(
                
                quantity = example_db.work_accessories.quantity - values_to_substract
            )
        )
    
    async def update_available_quantity_by_id(self,
        id: int,
        quantity: float
        ):

        await self.session.execute(
            update(
                
                example_db.material
                
            ).where(
                
                example_db.material.id == id
                
            ).values(
                
                quantity = quantity
            )
        )
       
    async def select_current_work_component_ids(self,
        work_id: int
        ) -> t.List[int]:
        
        query_result = await self.session.execute(
            select(
                
                example_db.work_accessories.component_id
                
            ).where(
                
                example_db.work_accessories.work_id == work_id,
            )
        )
        
        result = query_result.scalars().all()
        
        if result is not None:
            
            return result
        
        return []
    
    async def update_work_accessorie_quantity_by_id(self,
        work_id: int,
        material: MaterialData
        ):
        
        await self.session.execute(
            update(
                
                example_db.work_accessories
                
            ).where(
                and_(
                    example_db.work_accessories.work_id == work_id,
                    example_db.work_accessories.component_id == material.id
                )
            ).values(
                
                quantity = material.quantity
            )
        )
        
    async def insert_work_accessorie(self,
        work_id: int,
        material: MaterialData                                              
        ):
        
        await self.session.execute(
            insert(
                
                example_db.work_accessories
                
            ).values(
                
                work_id = work_id,
                component_id = material.id,
                quantity = material.quantity
            )
        )
        
    async def delete_work_accessorie_by_id(self,
        work_id: int,
        component_ids: t.List[int]
        ):

        await self.session.execute(
            delete(
                
                example_db.work_accessories
                
            ).where(
                and_(
                    example_db.work_accessories.work_id == work_id,
                    example_db.work_accessories.component_id.in_(component_ids)
                )
            )
        )
        
    async def update_available_quantity_by_removed_work_accessorie(self,
        quantity: float,
        id: int
        ):
        
        value_to_add = Decimal(str(quantity))
        
        await self.session.execute(
            update(
                
                example_db.material
                
            ).where(
                
                example_db.material.id == id
                
            ).values(
                
                quantity = example_db.material.quantity + value_to_add
            )
        )