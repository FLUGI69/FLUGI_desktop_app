from sqlalchemy import update, select, delete
from decimal import Decimal

import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.enums.hun_price_category_enum import HunPriceCategoryEnum
from utils.enums.hun_price_tier_enum import HunPriceTierEnum

class update_other_work_prices_hun(AsyncQueryBase):

    async def query(self,
        travel_budapest: Decimal,
        travel_outside_km: Decimal,
        tier_prices: t.Dict[HunPriceCategoryEnum, t.Dict[HunPriceTierEnum, Decimal]]
        ):
        
        result = await self.session.execute(
            select(example_db.other_work_prices_hun)
        )
        
        row = result.first()
        
        if row is not None:
            
            hun_prices: example_db.other_work_prices_hun = row[0]
            
            hun_prices.travel_budapest = travel_budapest
            hun_prices.travel_outside_km = travel_outside_km
            
            await self.session.execute(
                delete(
                    
                    example_db.other_work_prices_hun_tier
                    
                ).where(
                    
                    example_db.other_work_prices_hun_tier.hun_prices_id == hun_prices.id
                )
            )
            
            for category, tiers in tier_prices.items():
                
                for tier, price in tiers.items():
                    
                    self.session.add(example_db.other_work_prices_hun_tier(
                        hun_prices_id = hun_prices.id,
                        category = category,
                        tier = tier,
                        price = price
                    ))
        
        else:
            
            new_hun_prices = example_db.other_work_prices_hun(
                travel_budapest = travel_budapest,
                travel_outside_km = travel_outside_km
            )
            
            self.session.add(new_hun_prices)
            
            await self.session.flush()
            
            for category, tiers in tier_prices.items():
                
                for tier, price in tiers.items():
                    
                    self.session.add(example_db.other_work_prices_hun_tier(
                        hun_prices_id = new_hun_prices.id,
                        category = category,
                        tier = tier,
                        price = price
                    ))
        
        await self.session.commit()
