from sqlalchemy import select
from sqlalchemy.orm import selectinload, with_loader_criteria

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db

class select_all_tenant(AsyncQueryBase):

    async def query(self) -> t.Sequence[example_db.tenant]:

        unpaid_tenants_subquery = (
            select(
                
                example_db.rental_history.tenant_id
                
            ).where(
                
                example_db.rental_history.is_paid == False
            ).distinct().subquery()
        )

        result = await self.session.execute(
            select(
                
                example_db.tenant
                
            ).options(
                
                selectinload(example_db.tenant.tool),
                selectinload(example_db.tenant.device),
            
            ).where(
                
                example_db.tenant.returned == False,
                example_db.tenant.id.in_(
                    select(unpaid_tenants_subquery.c.tenant_id)
                )
                
            ).order_by(example_db.tenant.rental_end.asc())
        )

        return result.scalars().all()