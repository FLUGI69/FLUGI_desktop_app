from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    DateTime,
    Date, 
    Boolean, 
    ForeignKey, 
    BigInteger, 
    VARCHAR,
    Enum,
    func,
    and_,
    text
)
from sqlalchemy.dialects.mysql import LONGBLOB, DECIMAL
from sqlalchemy.orm import relationship, foreign

from utils.enums.ship_type_enum import ShipTypeEnum
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from utils.enums.tax_number_type_enum import TaxNumberTypeEnum
from db.db import MySQLDatabase

TableBase = MySQLDatabase.declarative_base("example_db")

class example_db:
    """All decimal values related to prices in the database are expressed in Hungarian Forints (HUF)."""
    
    class boat(TableBase): 
        
        """Required for the database initialization. 
            The 'boat' table must exist as a prerequisite, as it serves as the foundational entity. 
            If no boat entry exists, it is not possible to associate data with related tables, 
            ensuring referential integrity across the database schema."""
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        flag = Column(String(255), default = None)
        
        name = Column(String(255), nullable = False)
        
        ship_id = Column(Integer, nullable = False)
        
        imo = Column(Integer, default = None)
        
        mmsi = Column(Integer, default = None)
        
        callsign = Column(String(100), nullable = True, default = None)
        
        type_name = Column(String(100), nullable = True, default = None)
        
        view_on_map_href = Column(VARCHAR(600), nullable = True, default = None)
        
        more_deatails_href = Column(VARCHAR(600), nullable = True, default = None)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
          
        works = relationship("work", back_populates = "boat", lazy = "select")
        
        schedule = relationship("schedule", back_populates = "boat", cascade = "all, delete-orphan")

    class employee(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        name = Column(String(100), nullable = False, default = None)
        
        birth = Column(Date, nullable = False)
        
        taj_number = Column(String(20), nullable = False)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
    
    class work(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        boat_id = Column(BigInteger, ForeignKey("boat.id", ondelete = 'CASCADE'), comment = "ID in boats table")
        
        leader = Column(VARCHAR(255), nullable = False, comment = "Project leader") 
        
        description = Column(VARCHAR(1024), default = None)  
        
        start_date = Column(DateTime(timezone = True), nullable = True)
        
        finished_date = Column(DateTime(timezone = True), nullable = True)
        
        transfered = Column(Boolean, default = False, comment = "In progress - flag for note writing")
        
        is_contractor = Column(Boolean, default = False, comment = "Done by subcontractor")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        boat = relationship("boat", back_populates = "works")
        
        accessories = relationship("material", secondary = 'work_accessories', back_populates = "works")
        
        work_accessories = relationship(
            "work_accessories",
            lazy = "selectin",
            viewonly = True, 
            overlaps = "accessories"
        )
        
        status = relationship("work_status", uselist = False, back_populates = "work", cascade = "all, delete-orphan", lazy = "selectin")
        
        images = relationship(
            "work_img",
            back_populates = "works",
            cascade = "all, delete-orphan",
            lazy = "selectin"
        )

    class work_img(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        work_id = Column(BigInteger, ForeignKey("work.id", ondelete = 'CASCADE'), comment = "ID in works table")
        
        img = Column(LONGBLOB, default = None)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        works = relationship("work", back_populates = "images")
        
    class work_status(TableBase):
        # If it was transferred to our facility
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        work_id = Column(BigInteger, ForeignKey("work.id", ondelete = 'CASCADE'), unique = True)
        
        delivered_back = Column(Boolean(), default = False, comment = "Visszaadva")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        work = relationship("work", back_populates = "status")
        
        notes = relationship(
            "work_status_note",
            back_populates = "work_status",
            cascade = "all, delete-orphan",
            lazy = "joined"
        )
        
    class work_status_note(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        work_status_id = Column(BigInteger, ForeignKey("work_status.id", ondelete = 'CASCADE'))
        
        note = Column(VARCHAR(1024), nullable = False, comment = "Event flow (e.g., something was assigned to it)")  
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")

        work_status = relationship("work_status", back_populates = "notes")
    
    class other_work_prices(TableBase):
        """You have to set the prices for the price quotation in this table, otherwise the price quotation will not work and will throw an error, 
        because it requires a record to be present in this table to retrieve the prices for the price quotation. Default value is Euro (EUR)."""
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        work_during_hours = Column(DECIMAL(12, 2), nullable = True, comment = "Work during regular hours")
        
        work_outside_hours = Column(DECIMAL(12, 2), nullable = True, comment = "Work outside regular hours and on Saturday")
        
        work_sundays = Column(DECIMAL(12, 2), nullable = True, comment = "Sunday and holiday +100%")
        
        travel_budapest = Column(DECIMAL(12, 2), nullable = True, comment = "Travel within Budapest area")
    
        travel_outside = Column(DECIMAL(12, 2), nullable = True, comment = "Travel outside Budapest / abroad")
        
        travel_time = Column(DECIMAL(12, 2), nullable = True, comment = "Travel time")
        
        travel_time_outside = Column(DECIMAL(12, 2), nullable = True, comment = "Travel time outside regular hours and on Saturday +50%")
        
        travel_time_sundays = Column(DECIMAL(12, 2), nullable = True, comment = "Travel time on Sunday and holiday +100%")
        
        accommodation = Column(DECIMAL(12, 2), nullable = True, comment = "Accommodation")
    
    class client(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        name = Column(VARCHAR(250), nullable = False)
        
        address = Column(String(255), nullable = False, comment = "Address")
        
        country = Column(String(80), nullable = False)
        
        tax_number = Column(String(32), nullable = False)
        
        tax_number_raw = Column(String(64), nullable = True) 
        
        tax_number_type = Column(Enum(TaxNumberTypeEnum, native_enum = False), nullable = False)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        quotations = relationship("quotation", back_populates = "client")
    
    class quotation(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        cliient_id = Column(BigInteger, ForeignKey("client.id", ondelete = "CASCADE"), nullable = False)
        
        project_description = Column(VARCHAR(1024), nullable = False)
        
        other_information = Column(VARCHAR(1024), nullable = False)
          
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        client = relationship("client", back_populates = "quotations")
    
        order_number = relationship("order_number", back_populates="quotation", uselist = False)
    
    class order_number(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        quotation_id = Column(BigInteger, ForeignKey("quotation.id", ondelete = "CASCADE"), nullable = False)
        
        order_number = Column(String(20), unique = True, nullable = False)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
         
        quotation = relationship("quotation", back_populates = "order_number")
        
    class storage(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        name = Column(VARCHAR(1024), nullable = False)
        
        location = Column(String(255), nullable = False, comment = "Address or identifier")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        materials = relationship("material", back_populates = "storage", lazy = "select")
        
        tools = relationship("tool", back_populates = "storage", lazy = "select")
        
        devices = relationship("device", back_populates = "storage", lazy = "select")
        
        returnable_packagings = relationship("returnable_packaging", back_populates = "storage", lazy = "select")
            
    class material(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        storage_id = Column(BigInteger, ForeignKey("storage.id", ondelete = "CASCADE"), nullable = False)
        
        name = Column(VARCHAR(1024), default = None)
        
        manufacture_number = Column(String(100), nullable = True, default = None, comment = "Product number")
        
        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Quantity")
        
        unit = Column(String(100), nullable = True, default = None, comment = "Unit of measurement")
        
        manufacture_date = Column(DateTime(timezone = True), comment = "Manufacturing date")
        
        price = Column(DECIMAL(12, 2), nullable = True, comment = "Net unit price")
        
        purchase_source = Column(String(255), nullable = True, comment = "Purchase source")
        
        purchase_date = Column(DateTime, nullable = False, comment = "Purchase date")
        
        inspection_date = Column(DateTime(timezone = True), nullable = False, default = func.now(), comment = "Inspection date")
        
        is_deleted = Column(Boolean, default = False, comment = "Deleted")
        
        deleted_date = Column(DateTime(timezone = True), nullable = True, default = None, comment = "Deletion date")
        
        uuid = Column(LONGBLOB, default = None)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        works = relationship("work", secondary = 'work_accessories', back_populates = "accessories", overlaps="work_accessories")
        
        storage = relationship("storage", back_populates = "materials", lazy = "subquery")
        
    class work_accessories(TableBase):

        work_id = Column(BigInteger, ForeignKey("work.id", ondelete = 'CASCADE'), primary_key = True)
        
        component_id = Column(BigInteger, ForeignKey("material.id", ondelete = 'CASCADE'), primary_key = True)
        
        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Quantity")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
    class tool(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        storage_id = Column(BigInteger, ForeignKey("storage.id", ondelete = "CASCADE"), nullable = False)
        
        name = Column(VARCHAR(1024), default = None)
        
        manufacture_number = Column(String(100), nullable = True, default = None, comment = "Product number")
        
        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Quantity")
        
        manufacture_date = Column(DateTime(timezone = True), comment = "Manufacturing date")
        
        price = Column(DECIMAL(12, 2), nullable = True, comment = "Net unit price")
        
        commissioning_date = Column(DateTime(timezone = True), comment = "Commissioning date")
        
        purchase_source = Column(String(255), nullable = True, comment = "Purchase source")
        
        purchase_date = Column(DateTime, nullable = False, comment = "Purchase date")
        
        inspection_date = Column(DateTime(timezone = True), nullable = False, default = func.now(), comment = "Inspection date")
        
        is_scrap = Column(Boolean, default = False, comment = "Scrapped")
        
        is_deleted = Column(Boolean, default = False, comment = "Deleted")
        
        deleted_date = Column(DateTime(timezone = True), nullable = True, default = None, comment = "Deletion date")
        
        uuid = Column(LONGBLOB, default = None)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        tenant = relationship(
            "tenant", 
            primaryjoin = lambda: and_(
                foreign(example_db.tenant.item_id) == example_db.tool.id,
                example_db.tenant.item_type == StorageItemTypeEnum.TOOL
            ),            
            back_populates = "tool",
            cascade = "all, delete-orphan",
            overlaps = "tenant, device",
            uselist = True 
        )
        
        storage = relationship("storage", back_populates = "tools", lazy = "subquery")
    
    class device(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        storage_id = Column(BigInteger, ForeignKey("storage.id", ondelete = "CASCADE"), nullable = False)
        
        name = Column(VARCHAR(1024), default = None)
        
        manufacture_number = Column(String(100), nullable = True, default = None, comment = "Product number")
        
        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Quantity")
        
        manufacture_date = Column(DateTime(timezone = True), comment = "Manufacturing date")
        
        price = Column(DECIMAL(12, 2), nullable = True, comment = "Net unit price")
        
        commissioning_date = Column(DateTime(timezone = True), comment = "Commissioning date")
        
        purchase_source = Column(String(255), nullable = True, comment = "Purchase source")
        
        purchase_date = Column(DateTime, nullable = False, comment = "Purchase date")
        
        inspection_date = Column(DateTime(timezone = True), nullable = False, default = func.now(), comment = "Inspection date")
        
        is_scrap = Column(Boolean, default = False, comment = "Scrapped")
        
        is_deleted = Column(Boolean, default = False, comment = "Deleted")
        
        deleted_date = Column(DateTime(timezone = True), nullable = True, default = None, comment = "Deletion date")
        
        uuid = Column(LONGBLOB, default = None)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
 
        tenant = relationship(
            "tenant", 
            primaryjoin = lambda: and_(
                foreign(example_db.tenant.item_id) == example_db.device.id,
                example_db.tenant.item_type == StorageItemTypeEnum.DEVICE
            ),             
            back_populates = "device",
            cascade = "all, delete-orphan",
            overlaps = "tenant, tool",
            uselist = True
        )
        
        storage = relationship("storage", back_populates = "devices", lazy = "subquery")
    
    class returnable_packaging(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        storage_id = Column(BigInteger, ForeignKey("storage.id", ondelete = "CASCADE"), nullable = False)

        name = Column(VARCHAR(1024), default = None)
        
        manufacture_number = Column(String(100), nullable = True, default = None, comment = "Bottle/Container number")

        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Quantity")

        manufacture_date = Column(DateTime(timezone = True), comment = "Manufacturing date")
        
        price = Column(DECIMAL(12, 2), nullable = True, comment = "Net unit price")
        
        purchase_source = Column(String(255), nullable = True, comment = "Purchase source")

        purchase_date = Column(DateTime, nullable = False, comment = "Purchase date")

        inspection_date = Column(DateTime(timezone = True), nullable = False, default = func.now(), comment = "Inspection date")

        returned_date = Column(DateTime(timezone = True), nullable = True, default = None, comment = "Return date")

        is_returned = Column(Boolean, default = False, comment = "Returned")
        
        is_deleted = Column(Boolean, default = False, comment = "Deleted")
        
        deleted_date = Column(DateTime(timezone = True), nullable = True, default = None, comment = "Deletion date")

        uuid = Column(LONGBLOB, default = None)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        storage = relationship("storage", back_populates = "returnable_packagings", lazy = "subquery")
        
    class returned_packaging_history(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        returnable_packaging_id = Column(BigInteger, ForeignKey("returnable_packaging.id", ondelete = "CASCADE"), nullable = False)
        
        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Returned quantity")

        returned_date = Column(DateTime(timezone = True), nullable = False, default = func.now(), comment = "Return date")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")

    class tenant(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        item_type = Column(Enum(StorageItemTypeEnum, native_enum = False), nullable = False)
        
        item_id = Column(BigInteger, nullable = False)
        
        tenant_name = Column(String(255), nullable = False, comment = "Tenant name")
        
        rental_start = Column(DateTime(timezone = True), nullable = False, default = func.now(), comment = "Rental start date")
        
        rental_end = Column(DateTime(timezone = True), nullable = True, comment = "Requested until")
        
        returned = Column(Boolean, default = False, comment = "Returned")
        
        rental_price = Column(DECIMAL(12, 2), nullable = True, comment = "Net rental price HUF")
        
        quantity = Column(DECIMAL(10, 4), nullable = False, default = "0.0000", comment = "Quantity")
        
        is_daily_price = Column(Boolean, default = False, comment = "Daily rate")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        tenant_reminders = relationship(
            "tenant_reminder",
            back_populates = "tenant",
            lazy = "selectin",
            cascade = "all, delete-orphan"
        )
        
        tool = relationship(
            "tool", 
            primaryjoin = lambda: and_(
                foreign(example_db.tenant.item_id) == example_db.tool.id,
                example_db.tenant.item_type == StorageItemTypeEnum.TOOL
            ),        
            back_populates = "tenant",
            overlaps = "device, tenant"
        )
        
        device = relationship(
            "device", 
            primaryjoin = lambda: and_(
                foreign(example_db.tenant.item_id) == example_db.device.id,
                example_db.tenant.item_type == StorageItemTypeEnum.DEVICE
            ),            
            back_populates = "tenant",
            overlaps = "tool, tenant"
        )
        
        rental_histories = relationship(
            "rental_history", 
            back_populates =  "tenant",
            cascade = "all, delete-orphan"
        )
        
    class rental_history(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        tenant_id = Column(BigInteger, ForeignKey("tenant.id", ondelete = 'CASCADE'), nullable = False)
        
        is_paid = Column(Boolean, default = False, comment = "Paid")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        tenant = relationship(
            "tenant",
            back_populates = "rental_histories", 
            lazy = "joined"
        )
 
    class schedule(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        boat_id = Column(BigInteger, ForeignKey("boat.id", ondelete = 'CASCADE'), nullable = False, comment = "ID in boats table")
        
        location = Column(String(255), nullable = False)
        
        arrived_date = Column(DateTime(timezone = True), nullable = False, default = func.now())
        
        ponton = Column(String(255), nullable = False)
        
        leave_date = Column(DateTime(timezone = True), nullable = False, default = func.now())
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        boat = relationship("boat", back_populates = "schedule")  
        
    class calendar(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        note = Column(VARCHAR(1024), nullable = False)
        
        reminder_date = Column(DateTime(timezone = True), nullable = False, default = func.now())
        
        used = Column(Boolean, default = False)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        tenant_reminders = relationship(
            "tenant_reminder",
            back_populates = "calendar",
            lazy = "selectin",
            cascade = "all, delete-orphan"
        )
    
    class tenant_reminder(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        calendar_id = Column(BigInteger, ForeignKey("calendar.id", ondelete = 'CASCADE'), nullable = False, comment = "ID in calendar table")

        tenant_id = Column(BigInteger, ForeignKey("tenant.id", ondelete = 'CASCADE'), nullable = False, comment = "ID in tenant table")
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        calendar = relationship(
            "calendar",
            back_populates = "tenant_reminders",
            lazy = "joined"
        )
        
        tenant = relationship(
            "tenant",
            back_populates = "tenant_reminders",
            lazy = "joined"
        )

    class user_device(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        username = Column(String(255), nullable = True, unique = True)
        
        guid = Column(String(255), nullable = False, unique = True, comment = "Globally Unique Identifier")
        
        device_name = Column(String(255), nullable = True)
        
        os = Column(String(255), nullable = True)
        
        ip_address = Column(String(50), nullable = True)
        
        location = Column(String(255), nullable = True)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")

        login_histories = relationship(
            "login_history", 
            back_populates = "user_device", 
            lazy = "subquery", 
            cascade = "all, delete-orphan"
        )
        
        tokens = relationship(
            "google_token", 
            back_populates = "user_device", 
            lazy = "subquery", 
            cascade = "all, delete-orphan"
        )

    class login_history(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        user_device_id = Column(BigInteger, ForeignKey("user_device.id", ondelete = "CASCADE"), nullable = False)
        
        login_time = Column(DateTime(timezone = True), default = func.now(), nullable = False)
        
        success = Column(Boolean, default = True)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")

        user_device = relationship(
            "user_device", 
            back_populates = "login_histories", 
            lazy = "joined"
        )
        
        tokens = relationship(
            "google_token", 
            back_populates = "login_history", 
            lazy = "subquery", 
            cascade = "all, delete-orphan"
        )

    class scope(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        name = Column(String(512), nullable = False, unique = True)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")

        tokens = relationship(
            "google_token", 
            secondary = "token_scope", 
            lazy = "subquery", 
            back_populates = "scopes"
        )

    class google_token(TableBase):
        
        id = Column(BigInteger, autoincrement = True, primary_key = True)
        
        user_device_id = Column(BigInteger, ForeignKey("user_device.id", ondelete = "CASCADE"), nullable = False)
        
        login_history_id = Column(BigInteger, ForeignKey("login_history.id", ondelete = "CASCADE"), nullable=False)

        token = Column(VARCHAR(2048), nullable = False)
        
        refresh_token = Column(VARCHAR(2048), nullable = False)
        
        token_uri = Column(String(255), nullable = False)
        
        client_id = Column(String(255), nullable = False)
        
        client_secret = Column(String(255), nullable = False)
        
        expiry = Column(DateTime(timezone = True), nullable = True)
        
        universe_domain = Column(String(255), nullable = True)
        
        is_active = Column(Boolean, default = True)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")
        
        user_device = relationship("user_device", back_populates = "tokens", lazy = "joined")
        
        login_history = relationship("login_history", back_populates = "tokens", lazy = "joined")
        
        scopes = relationship(
            "scope", 
            secondary = "token_scope", 
            lazy = "subquery",
            back_populates = "tokens"
        )

    class token_scope(TableBase):
        
        token_id = Column(BigInteger, ForeignKey("google_token.id", ondelete = "CASCADE"), primary_key = True)
        
        scope_id = Column(BigInteger, ForeignKey("scope.id", ondelete = "CASCADE"), primary_key = True)
        
        created_at = Column(DateTime, default = func.now(), nullable = False, comment = "Creation timestamp")
        
        updated_at = Column(DateTime, default = func.now(), onupdate = func.now(), nullable = False, comment = "Last modification timestamp")