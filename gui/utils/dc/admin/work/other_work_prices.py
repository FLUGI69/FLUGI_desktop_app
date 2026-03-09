from decimal import Decimal

from dataclass import DataclassBaseModel

class OtherWorkPrices(DataclassBaseModel):
    work_during_hours: Decimal
    work_outside_hours: Decimal
    work_sundays: Decimal
    travel_budapest: Decimal
    travel_outside: Decimal
    travel_time: Decimal
    travel_time_outside: Decimal
    travel_time_sundays: Decimal
    accommodation: Decimal