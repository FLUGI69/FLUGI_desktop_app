from sqlalchemy import select
from sqlalchemy.orm import joinedload, load_only, noload

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_all_works(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.work]:
    
        query_result = (
            select(
                
                example_db.work
                
            ).options(
                
                load_only(
                    
                    example_db.work.id,
                    example_db.work.boat_id,
                    example_db.work.description,
                    example_db.work.start_date,
                    example_db.work.finished_date,
                    example_db.work.transfered,
                    example_db.work.is_contractor
                ),
                
                joinedload(
                    
                    example_db.work.boat
                    
                ).load_only(
                    
                    example_db.boat.name
                ),
                
                noload(example_db.work.accessories),
                noload(example_db.work.work_accessories),
                noload(example_db.work.status),
                noload(example_db.work.images)
            )
        )

        result = await self.session.execute(query_result)
        
        return result.unique().scalars().all()
        