from sqlalchemy import update, select, and_
from sqlalchemy.orm import selectinload, with_loader_criteria
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math 
import typing as t

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from utils.dc.admin.current_tenant import CurrentTenant
from utils.dc.admin.rental_history import RentalHistoryData
from utils.dc.tools import ToolsData
from utils.dc.device import DeviceData
from utils.dc.admin.period_info import PeriodInfo
from utils.dc.admin.reminder import CalendarData
from exceptions import InsufficientQuantityError
from exceptions import RentalPeriodExpiredError
from config import Config

class update_tenant_by_id(AsyncQueryBase):
    
    async def query(self,
        tenant_id: int,
        item_type: StorageItemTypeEnum,
        current_quantity: float,
        current_rental_start: datetime,
        current_price: float,
        new_quantity: float,
        new_price: float,
        is_daily_price: bool,
        current_rental_end: datetime | None = None,
        new_rental_end: datetime | None = None,
        ) -> None:

        now = datetime.now()
        
        if current_rental_end is not None and current_rental_end < now:
            
            raise RentalPeriodExpiredError(
                current_end_date = current_rental_end,
                now = now
            )
        
        changes_detected = False
        
        total_price, period_info = self.__calculate_total_price(
            now = now,
            base_price = current_price,
            new_price = new_price,
            current_quantity = current_quantity,
            new_quantity = new_quantity,
            current_rental_start = current_rental_start,
            current_rental_end = current_rental_end,
            new_rental_end = new_rental_end,
            is_daily_price = is_daily_price
        )
     
        async with self.session.begin():
            
            if period_info is not None:
               
                if current_rental_end != new_rental_end or (is_daily_price == True and current_rental_end is None):
                    
                    changes_detected = True
                    
                    await self._handle_date_extension(
                        tenant_id = tenant_id, 
                        new_rental_end = new_rental_end if new_rental_end is not None else period_info.period_end, 
                        item_type = item_type,
                        current_rental_end = current_rental_end,
                        total_price = total_price,
                        is_daily_price = is_daily_price,
                        period_info = period_info
                    )

                if current_price != new_price:
                    
                    changes_detected = True
                        
                    await self._handle_price_change(
                        tenant_id = tenant_id,
                        item_type = item_type,
                        current_rental_end = current_rental_end,
                        total_price = total_price,
                        is_daily_price = is_daily_price,
                        period_info = period_info
                    )
                        
                if new_quantity != 0:
                    
                    changes_detected = True
                    
                    await self._handle_quantity_change(
                        tenant_id = tenant_id,
                        item_type = item_type,
                        current_rental_end = current_rental_end,
                        new_quantity = new_quantity,
                        total_price = total_price,
                        is_daily_price = is_daily_price,
                        period_info = period_info
                    )
                    
                if changes_detected == False:
                    
                    raise Exception("No changes detected - unexpected situation.")
    
    def __resolve_period(self,
        now: datetime,
        base_price: float, 
        new_price: float | None,
        new_quantity: float,
        current_rental_start: datetime,
        is_daily_price: bool,
        current_rental_end: datetime | None = None,
        new_rental_end: datetime | None = None,
        ):
    
        if is_daily_price == True:
            
            period_end = new_rental_end if new_rental_end is not None else now
        
            full_period_days = max(math.ceil((period_end - current_rental_start).total_seconds() / 86400), 1)
            extension_days = full_period_days
            
            total_days = max(math.ceil((period_end - current_rental_start).total_seconds() / 86400), 1)
            elapsed_days = max(math.ceil((now - current_rental_start).total_seconds() / 86400), 0)
            
            daily_base_price = base_price
            daily_new_price = new_price if new_price is not None else daily_base_price
            
            price_changed = (new_price is not None) and (new_price != base_price)
            quantity_changed = (new_quantity != 0)
            extended = True
                    
            remaining_days = max(total_days - elapsed_days, 0)
            
            return PeriodInfo(
                full_period_days = full_period_days,
                extension_days = extension_days,
                daily_base_price = daily_base_price,
                daily_new_price = daily_new_price,
                price_changed = price_changed, 
                quantity_changed = quantity_changed, 
                extended = extended, 
                elapsed_days = elapsed_days, 
                remaining_days = remaining_days, 
                total_days = total_days,
                period_end = period_end
            )
        
        elif is_daily_price == False:
        
            full_period_days = max(math.ceil((current_rental_end - current_rental_start).total_seconds() / 86400), 1)
            extension_days = max((new_rental_end - current_rental_end).days, 0) if new_rental_end is not None else 0
        
            daily_base_price = base_price / full_period_days
            daily_new_price = (new_price / full_period_days) if new_price is not None else daily_base_price
   
            price_changed = (new_price is not None) and (new_price != base_price)
            quantity_changed = (new_quantity != 0)
            extended = (extension_days > 0)
            
            period_end = new_rental_end if extended is True else current_rental_end
            
            total_days = max(math.ceil((period_end - current_rental_start).total_seconds() / 86400), 1)
            elapsed_days = max(math.ceil((now - current_rental_start).total_seconds() / 86400), 0)
            
            remaining_days = max(total_days - elapsed_days, 0)
            
            return PeriodInfo(
                full_period_days = full_period_days,
                extension_days = extension_days,
                daily_base_price = daily_base_price,
                daily_new_price = daily_new_price,
                price_changed = price_changed, 
                quantity_changed = quantity_changed, 
                extended = extended, 
                elapsed_days = elapsed_days, 
                remaining_days = remaining_days, 
                total_days = total_days
            )
            
    def __calculate_total_price(self,
        now: datetime,
        base_price: float, 
        new_price: float | None,
        current_quantity: float, 
        new_quantity: float,
        current_rental_start: datetime,
        is_daily_price: bool,
        current_rental_end: datetime | None = None,
        new_rental_end: datetime | None = None,
        ) -> t.Tuple[Decimal, PeriodInfo]:
        
        self.log.info("Calculate tenant total price -> BEGIN")
        
        base_price = Decimal(str(base_price))
        new_price = Decimal(str(new_price)) if new_price is not None else None
        current_quantity = Decimal(str(current_quantity))
        new_quantity = Decimal(str(new_quantity))
    
        period_info = self.__resolve_period(
            now = now,
            base_price = float(base_price),
            new_price = float(new_price) if new_price is not None else None,
            new_quantity = float(new_quantity),
            current_rental_start = current_rental_start,
            is_daily_price = is_daily_price,
            current_rental_end = current_rental_end,
            new_rental_end = new_rental_end
        )
        
        new_rental_end =  new_rental_end if new_rental_end is not None else current_rental_start + timedelta(days = period_info.total_days)
        
        self.log.debug("Current rental cost: %s, Changed rental price: %s, Currently rented quantity: %s, Changed rented quantity: %s, Rental start: %s, Rental end: %s, Extended rental end: %s" % (
            str(base_price),
            str(new_price),
            str(current_quantity),
            str(new_quantity),
            current_rental_start.strftime(Config.time.timeformat),
            current_rental_end.strftime(Config.time.timeformat) if current_rental_end is not None else "Unknown",
            new_rental_end.strftime(Config.time.timeformat)
            )
        )
   
        if period_info is not None:
                
            daily_base_price = Decimal(str(period_info.daily_base_price))
            daily_new_price = Decimal(str(period_info.daily_new_price))
            elapsed_days = Decimal(str(period_info.elapsed_days))
            remaining_days = Decimal(str(period_info.remaining_days))
            
            self.log.debug("Daily base price: %s -> Daily new price: %s" % (
                daily_base_price.quantize(Decimal("0.01")) if daily_base_price is not None else "None", 
                daily_new_price.quantize(Decimal("0.01")) if daily_new_price is not None else "None"
                )
            )
            
            self.log.debug("Full rental days: %s, Extension days: %s" % (
                period_info.full_period_days, 
                period_info.extension_days
                )
            )

            total_price = Decimal("0.00")
            
            self.log.debug("Price changed -> %s | Quantity changed -> %s | Extended -> %s | Initial total price before calculation: %s" % (
                str(period_info.price_changed),
                str(period_info.quantity_changed),
                str(period_info.extended),
                base_price.quantize(Decimal("0.01"))
            ))
            
            self.log.debug("Elapsed days: %s, Remaining days: %s, Total days: %s" % (
                elapsed_days, 
                remaining_days, 
                period_info.total_days
                )
            )
            
            total_price += daily_base_price * current_quantity * elapsed_days
        
            self.log.debug("Elapsed days cost added | Sub-total: %s" % total_price.quantize(Decimal("0.01")))

            if period_info.price_changed is True:
            
                total_price += daily_new_price * current_quantity * remaining_days
            
                self.log.debug("Remaining days cost added with new price | Sub-total: %s" % total_price.quantize(Decimal("0.01")))

            if period_info.price_changed is False:
            
                total_price += daily_base_price * current_quantity * remaining_days
            
                self.log.debug("Remaining days cost added with base price | Sub-total: %s" % total_price.quantize(Decimal("0.01")))
            
            if period_info.quantity_changed is True:
                
                if new_quantity > 0:
                    
                    if period_info.price_changed is True:
                        
                        total_price += daily_new_price * new_quantity * remaining_days
                        
                        self.log.debug("New quantity cost added with new price | Sub-total: %s" % total_price.quantize(Decimal("0.01")))
                
                    else:
                    
                        total_price += daily_base_price * new_quantity * remaining_days
                    
                        self.log.debug("New quantity cost added with base price | Sub-total: %s" % total_price.quantize(Decimal("0.01")))
            
            self.log.debug("Post-extension result | Total: %s" % total_price.quantize(Decimal("0.01")))
                
            self.log.info("Calculate tenant total price -> END")

            total_price = total_price.quantize(Decimal("0.01"), rounding = ROUND_HALF_UP)
            
            return total_price, period_info
    
    async def _handle_quantity_change(self,
        tenant_id: float,
        item_type: StorageItemTypeEnum,
        new_quantity: float,
        total_price: float,
        is_daily_price: bool,
        period_info: PeriodInfo,
        current_rental_end: datetime | None = None,
        ):

        current_tenant = await self.select_current_tenant(
            tenant_id = tenant_id,
            item_type = item_type,
            current_rental_end = current_rental_end,
            is_daily_price = is_daily_price,
            total_price = total_price,
            period_info = period_info
        ) 
  
        available_quantity = 0
        
        if current_tenant.tool is not None:
            
            available_quantity = current_tenant.tool.quantity
            
        elif current_tenant.device is not None:
            
            available_quantity = current_tenant.device.quantity
        
        if new_quantity > available_quantity:
            
            raise InsufficientQuantityError(
                available_quantity = available_quantity, 
                new_quantity = new_quantity
            )

        await self.session.execute(
            update(
                
                example_db.tenant
            
            ).where(
                
                example_db.tenant.id == current_tenant.id
            
            ).values(
                
                quantity = current_tenant.quantity + new_quantity,
                rental_price = total_price
            )
        )

        if item_type == StorageItemTypeEnum.TOOL and current_tenant.tool is not None:
            
            await self.session.execute(
                update(
                    
                    example_db.tool
                    
                ).where(
                    
                    example_db.tool.id == current_tenant.tool.storage_id
                    
                ).values(
                    
                    quantity = current_tenant.tool.quantity - new_quantity
                )
            )
        elif item_type == StorageItemTypeEnum.DEVICE and current_tenant.device is not None:
            
            await self.session.execute(
                update(
                    
                    example_db.device
                    
                ).where(
                    
                    example_db.device.id == current_tenant.device.storage_id
                    
                ).values(
                    
                    quantity = current_tenant.device.quantity - new_quantity
                )
            )
            
        if current_tenant.is_daily_price == True:
            
            await self.session.execute(
                update(
                    
                    example_db.tenant
                    
                ).where(
                    
                    example_db.tenant.id == current_tenant.id
                    
                ) .values(
                
                    is_daily_price = False
                )
            )
    
    async def _handle_price_change(self,
        tenant_id: int,
        item_type: StorageItemTypeEnum,
        total_price: float,
        is_daily_price: bool,
        period_info: PeriodInfo,
        current_rental_end: datetime | None = None,
        ):
        
        current_tenant = await self.select_current_tenant(
            tenant_id = tenant_id,
            item_type = item_type,
            current_rental_end = current_rental_end,
            is_daily_price = is_daily_price,
            total_price = total_price,
            period_info = period_info
        )
        
        await self.session.execute(
            update(
                
                example_db.tenant
                
            ).where(
                
                example_db.tenant.id == current_tenant.id
            
            ).values(
                
                rental_price = total_price
            )
        )
    
        if current_tenant.tenant_reminders is not None and current_tenant.is_daily_price == False:
            
            formatted_price = str(total_price.quantize(Decimal("0.01"), rounding = ROUND_HALF_UP))
    
            note = self.note_map(
                extension_time = None,
                current_tenant = current_tenant,
                item_type = item_type,
                formatted_price = formatted_price 
            ) 
            
            if note is not None:
                    
                await self.session.execute(
                    update(
                        
                        example_db.calendar
                        
                    ).where(
                        
                        example_db.calendar.id == current_tenant.tenant_reminders.id
                        
                    ).values(
                        
                        note = note
                    )
                )
                
        if current_tenant.is_daily_price == True:
            
            await self.session.execute(
                update(
                    
                    example_db.tenant
                    
                ).where(
                    
                    example_db.tenant.id == current_tenant.id
                    
                ) .values(
                
                    is_daily_price = False
                )
            )
    
    async def _handle_date_extension(self, 
        tenant_id: int, 
        new_rental_end: datetime, 
        item_type: StorageItemTypeEnum,
        total_price: float,
        is_daily_price: bool,
        period_info: PeriodInfo,
        current_rental_end: datetime | None = None,
        ):
        
        current_tenant = await self.select_current_tenant(
            tenant_id = tenant_id,
            item_type = item_type,
            current_rental_end = current_rental_end,
            is_daily_price = is_daily_price,
            total_price = total_price,
            period_info = period_info
        ) 
   
        await self.session.execute(
            update(
                
                example_db.tenant
                
            ).where(
                
                example_db.tenant.id == current_tenant.id
                    
            ).values(
                
                rental_price = total_price,
                rental_end = new_rental_end
            )
        )
        
        formatted_price = f"{total_price:,.2f}".replace(",", ".")
   
        note = self.note_map(
            extension_time = new_rental_end.strftime(Config.time.timeformat),
            current_tenant = current_tenant,
            item_type = item_type,
            formatted_price = formatted_price 
        ) 
        
        if note is not None and current_tenant.tenant_reminders is not None:
                 
            await self.session.execute(
                update(
                    example_db.calendar
                    
                ).where(
                    
                    example_db.calendar.id == current_tenant.tenant_reminders.id
                    
                ).values(
                    
                    reminder_date = new_rental_end,
                    note = note
                )
            )
            
        if current_tenant.is_daily_price == True:
            
            await self.session.execute(
                update(
                    
                    example_db.tenant
                    
                ).where(
                    
                    example_db.tenant.id == current_tenant.id
                    
                ) .values(
                
                    is_daily_price = False
                )
            )

    async def select_current_tenant(self, 
        tenant_id: int, 
        item_type: StorageItemTypeEnum,
        is_daily_price: bool,
        total_price: float,
        period_info: PeriodInfo,
        current_rental_end: datetime | None = None,
        ) -> CurrentTenant:
        
        statement = (
            select(
                
                example_db.tenant
                
            ).options(
                
                selectinload(example_db.tenant.rental_histories),
                selectinload(example_db.tenant.tool),
                selectinload(example_db.tenant.device)
                
            ).where(
                and_(
                    example_db.tenant.id == tenant_id,
                    example_db.tenant.item_type == item_type
                )
            )
        )
        
        if current_rental_end is not None and is_daily_price == False:
            
            statement = statement.options(
                selectinload(example_db.tenant.tenant_reminders)
                
                ).options(
                    with_loader_criteria(
                        example_db.calendar,
                        lambda calendar: and_(
                            calendar.used == False,
                            calendar.reminder_date == current_rental_end
                        )
                    ),
                )
        
        query_result = await self.session.execute(statement)
        
        result = query_result.scalar_one_or_none()
        
        if result is not None:
            
            if current_rental_end is None and isinstance(period_info, PeriodInfo) \
                and period_info.period_end is not None:
                
                formatted_price = f"{total_price:,.2f}".replace(",", ".")
                
                if item_type == StorageItemTypeEnum.TOOL:
                    
                    note = "Rental period expired for %s. Rented tool: %s (ID: %s). \
                        Rental period cost: %s HUF" % (
                            result.tenant_name,
                            result.tool.name,
                            str(result.item_id),
                            formatted_price
                        )
                if item_type == StorageItemTypeEnum.DEVICE:
                    
                    note = "Rental period expired for %s. Rented device: %s (ID: %s). \
                        Rental period cost: %s HUF" % (
                            result.tenant_name,
                            result.device.name,
                            str(result.item_id),
                            formatted_price
                        )
                
                new_calendar = example_db.calendar(
                    reminder_date = period_info.period_end,
                    used = False,
                    note = note
                )
                
                self.session.add(new_calendar)
                
                await self.session.flush()
                
                new_tenant_reminder = example_db.tenant_reminder(
                    tenant_id = result.id,
                    calendar_id = new_calendar.id
                )
                
                self.session.add(new_tenant_reminder)
                
                await self.session.flush()
    
                await self.session.refresh(result, ['tenant_reminders'])

            return CurrentTenant(
                id = result.id,
                tenant_name = result.tenant_name,
                rental_start = result.rental_start,
                rental_end = result.rental_end if result.rental_end is not None else period_info.period_end,
                rental_price = result.rental_price,
                item_type = result.item_type,
                item_id = result.item_id,
                returned = result.returned,
                quantity = result.quantity,
                is_daily_price = result.is_daily_price,
                tool = ToolsData(
                    storage_id = result.tool.storage_id,
                    name = result.tool.name,
                    manufacture_number = result.tool.manufacture_number,
                    quantity = result.tool.quantity,
                    manufacture_date = result.tool.manufacture_date,
                    price = result.tool.price,
                    commissioning_date = result.tool.commissioning_date,
                    purchase_source = result.tool.purchase_source,
                    inspection_date = result.tool.inspection_date,
                    is_scrap = result.tool.is_scrap
                ) if result.tool is not None else None,
                device = DeviceData(
                    storage_id = result.device.storage_id,
                    name = result.device.name,
                    manufacture_number = result.device.manufacture_number,
                    quantity = result.device.quantity,
                    manufacture_date = result.device.manufacture_date,
                    price = result.device.price,
                    commissioning_date = result.device.commissioning_date,
                    purchase_source = result.device.purchase_source,
                    inspection_date = result.device.inspection_date,
                    is_scrap = result.device.is_scrap
                ) if result.device is not None else None,
                rental_histories = RentalHistoryData(
                    is_paid = result.rental_histories[0].is_paid
                ) if result.rental_histories is not None and len(result.rental_histories) > 0 else None,
                tenant_reminders = CalendarData(
                    id = result.tenant_reminders[0].id,
                    note = result.tenant_reminders[0].calendar.note,
                    date = result.tenant_reminders[0].calendar.reminder_date,
                    used = result.tenant_reminders[0].calendar.used
                ) if (result.tenant_reminders is not None and len(result.tenant_reminders) > 0 
                    and result.tenant_reminders[0] is not None
                    and result.tenant_reminders[0].calendar is not None
                ) else None
            )
      
    def note_map(self,
        current_tenant: CurrentTenant,
        item_type: StorageItemTypeEnum,
        formatted_price: str,
        extension_time: datetime | None = None,
        ) -> str:
        
        current_note = None
        
        if current_tenant.tenant_reminders is not None:
            
            current_note = current_tenant.tenant_reminders.note
        
        if item_type == StorageItemTypeEnum.TOOL:
            
            item = current_tenant.tool.name

        if item_type == StorageItemTypeEnum.DEVICE:
            
            item = current_tenant.device.name
        
        note = current_note if current_note is not None else None
        
        if extension_time is not None:
            
            note = "Extension date: %s | Rental period expired for %s. Rented tool: %s (ID: %s). \
                Rental period cost: %s HUF" % (
                    extension_time,
                    current_tenant.tenant_name,
                    item,
                    str(current_tenant.item_id),
                    formatted_price
                )
        
        return note      
