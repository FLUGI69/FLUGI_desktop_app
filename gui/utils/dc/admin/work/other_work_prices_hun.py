from decimal import Decimal

from dataclass import DataclassBaseModel
from utils.enums.hun_price_category_enum import HunPriceCategoryEnum
from utils.enums.hun_price_tier_enum import HunPriceTierEnum

class HunPriceTier(DataclassBaseModel):
    weekday: Decimal
    weekend: Decimal
    sunday: Decimal

class OtherWorkPricesHun(DataclassBaseModel):
    survey_delivery: HunPriceTier
    repair_maintenance: HunPriceTier
    travel_time: HunPriceTier
    travel_budapest: Decimal
    travel_outside_km: Decimal
