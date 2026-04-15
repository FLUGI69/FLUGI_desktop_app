from sqlalchemy import update, exists, select, insert

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class update_work_transfered_by_id(AsyncQueryBase):
     
    async def query(self, 
        work_id: int,
        transfered: bool
        ):

        async with self.session.begin():
            
            await self.session.execute(
                update(
                    
                    example_db.work
                    
                ).where(
                    
                    example_db.work.id == work_id
                    
                ).values(
                    
                    transfered = transfered
                )
            )
            
            if transfered is True:
                
                work_status_exists = await self.session.execute(
                    select(
                        exists().where(
                            example_db.work_status.work_id == work_id
                        )
                    )
                )
                
                if not work_status_exists.scalar():
                    
                    await self.session.execute(
                        insert(
                            
                            example_db.work_status
                            
                        ).values(
                            
                            work_id = work_id,
                            delivered_back = False
                        )
                    )
