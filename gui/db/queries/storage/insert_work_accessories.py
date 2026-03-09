from sqlalchemy import insert, select, and_, update

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import  example_db

class insert_work_accessories(AsyncQueryBase):

    async def query(self, work_id: int, part_ids: list[int]):
        
        values_to_insert = [
            {"work_id": work_id, "component_id": part_id}
            for part_id in part_ids
        ]
        
        await self.session.execute(
            insert(
                
                example_db.work_accessories
                
            ).values(
                
                values_to_insert
            )
        )
        
        await self.session.commit()
    
    async def _select_accessories_by_id(self, id: int) -> example_db.material:
        
        query_result = await self.session.execute(
            select(
                
                example_db.material
                
            ).where(
                
                and_(
                    example_db.material.id == id
                )
            )
        )
        
        result = query_result.scalar()
        
        if result is not None:
            
            return result            