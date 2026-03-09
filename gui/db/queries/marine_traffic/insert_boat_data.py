from sqlalchemy import insert, exists, select, and_
import typing as t
from datetime import datetime
import logging

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.logger import LoggerMixin

class insert_boat_data(AsyncQueryBase, LoggerMixin):
    
    log: logging.Logger

    async def query(self, 
        flag: t.Optional[str],
        name: str,
        ship_id: int,
        imo: t.Optional[int],
        mmsi: t.Optional[int],
        type_name: t.Optional[str],
        callsign: t.Optional[str],
        more_deatails_href: t.Optional[str],
        view_on_map_href: t.Optional[str]
        ) -> None:

        is_exist = await self.select_boat_exist(
            name = name, 
            ship_id = ship_id
        )
        
        if is_exist == True:
            
            self.log.info("%s (%s) is already in the database, skipping insert of boat data" % (
                name, 
                str(ship_id)
                )
            )
            
            return
        
        else:
            
            await self.session.execute(
                insert(
                    
                    example_db.boat
                    
                ).values(
                    flag = flag,
                    name = name,
                    ship_id = ship_id,
                    imo = imo,
                    mmsi = mmsi,
                    callsign = callsign,
                    type_name = type_name,
                    more_deatails_href = more_deatails_href,
                    view_on_map_href = view_on_map_href
                )
            )
            
            await self.session.commit()
        
    async def select_boat_exist(self, name: str, ship_id: t.Optional[int]) -> bool:
    
        query_result = await self.session.execute(
            select(
                exists().where(
                    
                    and_(
                        example_db.boat.name == name,
                        example_db.boat.ship_id == ship_id
                    )   
                )   
            )
        )
        
        return query_result.scalar()