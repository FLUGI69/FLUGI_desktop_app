from sqlalchemy.orm import aliased, joinedload, noload, with_loader_criteria
from sqlalchemy import select, func, and_
from sqlalchemy.engine import Row

from datetime import datetime
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from config import Config

class select_work_images_by_work_id(AsyncQueryBase):

    async def query(self, id: int) -> t.Sequence[example_db.work_img]:

        query_result = await self.session.execute(
            select(
                
                example_db.work_img
                
            ).where(
                
                example_db.work_img.work_id == id
            )
        )
        
        return query_result.scalars().all()