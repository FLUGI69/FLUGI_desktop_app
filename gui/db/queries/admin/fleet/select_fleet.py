from sqlalchemy import and_, select, func
from sqlalchemy.orm import noload

import typing as t 
from datetime import datetime

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_fleet(AsyncQueryBase):

    async def query(self) -> t.Sequence[t.Tuple[example_db.boat, int]]:
        
        now = datetime.now()
        
        works_subquery = (
            select(
                example_db.work.boat_id,
                func.count(example_db.work.id).label("count_works")
            ).where(
                and_(
                    example_db.work.finished_date >= now,
                    example_db.work.boat_id == example_db.boat.id
                )
            ).group_by(example_db.work.boat_id).subquery()
        )
        
        query_result = (
            select(
                example_db.boat,
                func.coalesce(works_subquery.c.count_works, 0).label("count_works")
            ).outerjoin(
                works_subquery,
                works_subquery.c.boat_id == example_db.boat.id
            ).options(
                noload(example_db.boat.schedule)
            )
        )

        result = await self.session.execute(query_result)
        
        return result.all()
        