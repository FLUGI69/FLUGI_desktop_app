from datetime import datetime
import typing as t
from decimal import Decimal

from sqlalchemy.engine import Row

from PyQt6.QtCore import QDateTime

from utils.dc.material import MaterialData
from utils.dc.admin.work.status_note import AdminWorkStatusNote
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from utils.enums.tax_number_type_enum import TaxNumberTypeEnum
from db.tables import example_db

async def insert_work_by_boat_id(
    boat_id: int, 
    leader: str,
    description: str,
    is_contractor: bool,
    img_paths: list = [],
    materials: t.List[MaterialData] = []
) -> None: pass

async def insert_boat_data(
    flag: t.Optional[str],
    name: str,
    ship_id: int,
    imo: t.Optional[int],
    mmsi: t.Optional[int],
    type_name: t.Optional[str],
    callsign: t.Optional[str],
    more_deatails_href: t.Optional[str],
    view_on_map_href: t.Optional[str]
) -> None: pass

async def insert_boat_schedule(
    boat_id: int, 
    location: str, 
    arrived_date: datetime, 
    ponton: str, 
    leave_date: datetime
) -> None: pass

async def insert_material_data(
    storage_id: int, 
    name: str,
    manufacture_number: str, 
    quantity: float, 
    unit: str, 
    manufacture_date: datetime,
    price: float,
    purchase_source: str,
    purchase_date: datetime,
    inspection_date: datetime,
    is_deleted: bool,
    deleted_date: datetime,
    uuid: bytes
) -> None: pass

async def insert_work_accessories(
    work_id: int, 
    part_ids: list[int]
    ) -> None: pass

async def insert_reminder(
    note: str, 
    reminder_date: datetime,
    used: bool
) -> None: pass

async def insert_tools_data(
    storage_id: int,
    name: str, 
    manufacture_number: str, 
    quantity: float, 
    manufacture_date: datetime, 
    price: float,
    commissioning_date: datetime,
    purchase_source: str,
    purchase_date: datetime,
    inspection_date: datetime,
    is_scrap: bool,
    is_deleted: bool,
    deleted_date: datetime,
    uuid: bytes
) -> None: pass

async def insert_tenant(
    item_id: int,
    item_name: str,
    item_type: StorageItemTypeEnum, 
    item_quantity: float, 
    tenant_quantity: int,
    tenant_name: str,
    rental_start: datetime,
    rental_end: datetime,
    rental_price: float,
    is_daily_price: bool
) -> None: pass


async def insert_storage_data(name: str, location: str) -> None: pass

async def insert_user_device_token_login_info(
    guid: str,
    device_name: str, 
    os: str,
    ip_address: str,
    location: str,
    success: bool,             
    token: str, 
    refresh_token: str, 
    token_uri: str, 
    client_id: str, 
    client_secret: str, 
    expiry: datetime, 
    universe_domain: str,
    scopes: list[str],
    is_active: bool,
    username: str | None = None,
) -> None: pass

async def insert_tools_is_scrap(
    storage_id: int,
    name: str, 
    manufacture_number: str, 
    quantity: float, 
    manufacture_date: datetime, 
    price: float,
    commissioning_date: datetime,
    purchase_source: str, 
    inspection_date: datetime,
    is_scrap: bool,
    is_deleted: bool,
    deleted_date: datetime,
    previous_quantity: int
) -> None: pass

async def insert_devices_data(
    storage_id: int,
    name: str, 
    manufacture_number: str, 
    quantity: float, 
    manufacture_date: datetime, 
    price: float,
    commissioning_date: datetime,
    purchase_source: str,
    purchase_date: datetime,
    inspection_date: datetime, 
    is_scrap: bool,
    is_deleted: bool,
    deleted_date: datetime,
    uudi: bytes
    ) -> None: pass

async def insert_returnable_data(
    storage_id: int, 
    name: str,
    manufacture_number: str, 
    quantity: float, 
    manufacture_date: datetime,
    price: float,
    purchase_source: str,
    purchase_date: datetime,
    inspection_date: datetime,
    returned_date: datetime,
    is_returned: bool,
    is_deleted: bool,
    deleted_date: datetime,
    uuid: bytes
)  -> None: pass

async def insert_devices_is_scrap(
    storage_id: int,
    name: str, 
    manufacture_number: str, 
    quantity: float, 
    manufacture_date: datetime, 
    price: float,
    commissioning_date: datetime,
    purchase_source: str, 
    inspection_date: datetime,
    is_deleted: bool,
    deleted_date: datetime,
    is_scrap: bool,
    previous_quantity: float
) -> None: pass

async def insert_quotation_with_order(
    client_name: str,
    client_address: str,
    client_country: str,
    client_tax_number: str,
    client_tax_number_type: TaxNumberTypeEnum,
    project_description: str,
    other_information: str,
    client_tax_number_raw: str = None
) -> str: pass

async def update_work_by_id(
    work_id: int,
    leader: str | None,
    description: str | None,
    prev_transfered: bool,
    transfered: bool,
    is_contractor: bool | None,
    start_date: datetime | None,
    finished_date: datetime | None,
    new_note: str | None,
    new_imgs: t.List[str],
    work_accessories: t.List[MaterialData],
    deleted_work_material: t.List[MaterialData],
    available_materials: t.List[MaterialData],
    deleted_available_material: t.List[MaterialData],
    changed_notes: t.List[AdminWorkStatusNote] = [],
    deleted_img_bytes: dict = {}
) -> None: pass

async def update_material_data(
    id: int,
    inspection_date: datetime,
    storage_id: int | None = None,
    name: str | None = None,
    manufacture_number: str | None = None,
    quantity: float | None = None,
    unit: str | None = None,
    manufacture_date: datetime | None = None,
    price: float | None = None,
    purchase_source: str | None = None,
    purchase_date: datetime | None = None
) -> None: pass

async def update_calendar_by_id(
    id: int, 
) -> None: pass

async def update_reminder_datetime_by_id(
    id: int,
    datetime: datetime
) -> None: pass

async def update_tools_data(
    id: int,
    storage_id: int | None = None,
    name: str | None = None,
    quantity: float | None = None,
    manufacture_number: str | None = None,
    manufacture_date: datetime | None = None,
    commissioning_date: datetime | None = None,
    price: float | None = None,
    inspection_date: datetime | None = None,
    purchase_date: datetime | None = None
) -> None: pass

async def update_google_token_by_guid(
    guid: str, 
    token: str, 
    expiry: str
) -> None: pass

async def update_user_token_active_by_guid(
    guid: str, 
    is_active: bool
) -> None: pass

async def update_device_name_by_guid(guid: str, name: str) -> None: pass

async def update_rental_history_by_tenant_id(
    tenant_id: int, 
    item_type: StorageItemTypeEnum,
    tool_id: int,
    current_is_paid: bool,
    current_returned: bool,
    current_rental_start: datetime,
    current_rental_end: datetime,
    current_amount: float,
    rented_quantity: float,
    new_is_paid: bool = None, 
    new_returned: bool = None
) -> None: pass

async def update_tenant_by_id(
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
): pass

async def update_devices_data(
    id: int,
    storage_id: int | None = None,
    name: str | None = None,
    quantity: float | None = None,
    manufacture_number: str | None = None,
    manufacture_date: datetime | None = None,
    commissioning_date: datetime | None = None,
    price: float | None = None,
    inspection_date: datetime | None = None,
    purchase_source: str | None = None
) -> None: pass

async def update_returnable_data(
    id: int,
    storage_id: int | None = None,
    name: str | None = None,
    quantity: float | None = None,
    manufacture_number: str | None = None,
    manufacture_date: datetime | None = None,
    commissioning_date: datetime | None = None,
    price: float | None = None,
    inspection_date: datetime | None = None,
    purchase_date: datetime | None = None
) -> None: pass

async def update_returnable_packaging_returned_by_id(
    id: int,
    quantity: float
) -> None: pass

async def update_schedule_by_id(
    id: int, 
    values_to_update: dict
) -> None: pass

async def update_other_work_prices(
        work_during_hours: Decimal,
        work_outside_hours: Decimal,
        work_sundays: Decimal,
        travel_budapest: Decimal,
        travel_outside: Decimal,
        travel_time: Decimal,
        travel_time_outside: Decimal,
        travel_time_sundays: Decimal,
        accommodation: Decimal
) -> None: pass

async def select_daily_tasks_from_boats() -> t.Sequence[Row[t.Tuple[example_db.boat, example_db.schedule]]]: pass

async def select_min_future_arrival_date() -> t.Optional[datetime]: pass

async def select_boat_by_name(boat_name: str) -> t.Sequence[example_db.boat]: pass

async def select_material_data() -> t.Sequence[example_db.material]: pass

async def select_boat_work_by_boat_name(boat_name: str) -> t.Sequence[example_db.work]: pass

async def select_all_boats() -> t.Sequence[example_db.boat]: pass

async def select_all_works() -> list | None: pass

async def select_reminders_data() -> t.Sequence[example_db.calendar]: pass

async def select_tools_data() -> t.Sequence[example_db.tool]: pass

async def select_all_storage() -> t.Sequence[example_db.storage]: pass

async def select_all_storage_items() -> t.Sequence[example_db.storage]: pass # selectinload: materials, tools - tenant, devices - tenant

async def select_google_token_exists(guid: str) -> example_db.google_token | None: pass

async def select_current_device_by_guid(guid: str) -> example_db.user_device | None: pass

async def select_all_tenant() -> t.Sequence[example_db.tenant]: pass

async def select_all_rental_history() -> t.Sequence[example_db.rental_history]: pass

async def select_devices_data() -> t.Sequence[example_db.device]: pass

async def select_returnable_packaging_data() -> t.Sequence[example_db.returnable_packaging]: pass

async def select_next_possible_row_tool_id() -> int: pass

async def select_next_possible_row_device_id() -> int: pass

async def select_next_possible_row_material_id() -> int: pass

async def select_next_possible_row_returned_packaging_id() -> int: pass

async def select_existing_other_work_prices() -> Row[t.Tuple[example_db.other_work_prices]]: pass

async def select_schedule_by_boat_name(boat_name: str) -> t.Sequence[example_db.boat]: pass

async def select_work_status_by_work_id(id: int) -> example_db.work_status | None: pass

async def select_work_images_by_work_id(id: int) -> t.Sequence[example_db.work_img]: pass

async def select_next_order_number_preview() -> str: pass

async def select_all_clients() -> t.Sequence[example_db.client]: pass

async def select_client_by_id(client_id: int) -> t.Optional[example_db.client]: pass

async def delete_items_by_id_from_specified_table(
    items_by_type: t.Dict[StorageItemTypeEnum, t.List[int]]
) -> None: pass