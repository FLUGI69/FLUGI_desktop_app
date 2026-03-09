from sqlalchemy import update, exists, and_, select
from datetime import datetime
import logging
import typing as t
from collections import Counter

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.logger import LoggerMixin
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from exceptions import ItemCannotBeDeletedWhileRentedError
from config import Config

class delete_items_by_id_from_specified_table(AsyncQueryBase, LoggerMixin):

    log: logging.Logger
    
    async def query(self, 
        items_by_type: t.Dict[StorageItemTypeEnum, t.List[int]]
        ):

        table_type = {
            StorageItemTypeEnum.MATERIAL: example_db.material,
            StorageItemTypeEnum.TOOL: example_db.tool,
            StorageItemTypeEnum.DEVICE: example_db.device,
            StorageItemTypeEnum.RETURNABLE_PACKAGING: example_db.returnable_packaging,
        }
        
        for items_type, ids in items_by_type.items():
            
            if len(ids) > 0:
                
                table: t.Union[
                    example_db.material,
                    example_db.tool,
                    example_db.device,
                    example_db.returnable_packaging
                ] = table_type.get(items_type)
        
                if table is not None:
                    
                    if items_type.value == "MATERIAL":
                        
                        work_components_exist_stmt = select(
                            exists().where(
                                
                                example_db.work_accessories.component_id.in_(ids)
                            )
                        )

                        result = await self.session.execute(work_components_exist_stmt)
                        
                        work_components_exist = result.scalar()
                        
                        if work_components_exist == True:
                            raise ItemCannotBeDeletedWhileRentedError("Material")
                                        
                    active_items_stmt = (
                        select(
                            
                            table.id, table.name
                            
                        ).join(
                            
                            example_db.tenant,
                            
                            and_(
                                
                                example_db.tenant.item_id == table.id,
                                example_db.tenant.item_type == items_type,
                                example_db.tenant.returned == False
                            )
                            
                        ).where(table.id.in_(ids))
                    )
                    
                    result = await self.session.execute(active_items_stmt)
                    
                    rows = result.fetchall()
                    
                    if len(rows) > 0:
                        
                        item_list = [f"{row.name}({row.id})" for row in rows]
    
                        counts = Counter(item_list)
                        
                        items_str = ", ".join(f"{item} - {count}" for item, count in counts.items())
                        
                        raise ItemCannotBeDeletedWhileRentedError(items = items_str)
                    
                    await self.session.execute(
                        update(
                            
                            table
                            
                        ).where(
                            
                            table.id.in_(ids)
                            
                        ).values(
                            
                            is_deleted = True,
                            deleted_date = datetime.now(Config.time.timezone_utc)
                        )
                    )
                    
                    await self.session.commit()
          