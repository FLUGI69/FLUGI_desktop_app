import os
import sys
from sqlalchemy import sql, Column, text, func, select, Enum, Engine, create_engine
from sqlalchemy import inspect, Inspector
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base as default_declarative_base
from sqlalchemy.orm.decl_api import DeclarativeMeta as DefaultDeclarativeMeta
from sqlalchemy.exc import OperationalError
import time

from pathlib import Path
import types
import typing
from pkgutil import iter_modules
import pylibimport
import inspect as insp
from types import ModuleType
import logging

from utils.logger import LoggerMixin
from .async_query_base import AsyncQueryBase, AsyncQueryCallback
from .query_base import QueryBase, QueryCallback
from .async_session import AsyncSessionMaker, AsyncSession
from .session import Session, SessionMaker
from .network.connections import SSHTunnelConnections, SSHTunnelConnection
from .network.reconnect_service import SSHTunnelReconnectService
from .network.sshtunnel import SSHTunnel
from .string import String
from db import queries

Tables = {}

class MySQLDatabase(LoggerMixin):
    
    engine: Engine = None
    
    async_engine: AsyncEngine = None

    log: logging.Logger

    def __init__(self,
        tables = None, 
        encoding = 'utf8', 
        auto_create_db: bool = False, 
        auto_create_tables: bool = False, 
        auto_add_new_columns: bool = False,
        general_log: bool = False,
        query_timer: bool = True,
        session: bool = True,
        sql_type = "mysql", 
        mysql_engine = "InnoDB", 
        mysql_charset = 'latin2', 
        check_column_parameters: bool = False,
        create_engine_extra_kwargs: dict = {},
        sessionmaker_extra_kwargs: dict = {},
        async_create_engine_extra_kwargs: dict = {},
        async_sessionmaker_extra_kwargs: dict = {},
        **_kwargs
        ):
      
        if tables is None or tables is object:
            
            from db.tables import example_db as example_db_tables
            
            class Tables: pass 
        
            tables = Tables()
     
            for attr_name in dir(example_db_tables):
                
                if not attr_name.startswith('_'):
                    
                    attr = getattr(example_db_tables, attr_name)
                    
                    if isinstance(attr, type):
                        
                        setattr(tables, attr_name, attr)
            
        self.__dbName = None
        
        self.ssh_tunnel = None
        
        self.ssh_tunnel_reconnect_service = None
        
        self.async_engine = None
        
        self.Session = None
        
        self.AsyncSession = None
        
        self.engine = None
        
        self._tables = tables
        
        self.tables_metaclasses = {name: getattr(tables, name) for name in dir(tables) \
            if not name.startswith('_') and isinstance(getattr(tables, name), type)}
        
        self.queries = Queries()
        
        self.general_log = general_log
        
        self.encoding = encoding
        
        self.sqlType = sql_type
        
        self.autoCreateDB = auto_create_db
        
        self.autoCreateTables = auto_create_tables
        
        self.mysql_engine = mysql_engine
        
        self.mysql_charset = mysql_charset
        
        self.checkColumnParameters = check_column_parameters
        
        self.autoAddNewColumns = auto_add_new_columns
        
        self.create_engine_extra_kwargs = create_engine_extra_kwargs
        
        self.sessionmaker_extra_kwargs = sessionmaker_extra_kwargs

        self.async_create_engine_extra_kwargs = async_create_engine_extra_kwargs
        
        self.async_sessionmaker_extra_kwargs = async_sessionmaker_extra_kwargs
        
        self.queryTimer = query_timer
        
        self.__set_async_engine = False
        
        self.session_enabled = session

        if 'queries_path' in _kwargs:
            
            self.queries_path = _kwargs['queries_path']
            
        else:
            
            if getattr(sys, "frozen", False):
             
                base_path = Path(sys.executable).parent / "_internal" / "gui" / "db"
                
            else:
        
                base_path = Path(__file__).parent
               
            self.queries_path = base_path / 'queries'
            
        # for name in dir(self._tables):
            
        #     if not name.startswith('_'):
                
        #         attr = getattr(self._tables, name)
                
        #         if isinstance(attr, type):
                    
        #             print(f"Table: {name}, Class: {attr.__name__}")
        
    @property
    def tables(self):
        
        return self._tables
                       
    @property
    def tableBase(self):
        
        return Tables[self.__dbName]["base"]
    
    @classmethod
    def __str__(cls) -> str:
        
        return cls.__name__

    class Timer:

        def start():
            
            start_time = time.time()
            
            return start_time

        def stop(start_time):
            
            stop_time = time.time() - start_time
            #print("Time: %s sec" % (end_time))
            
            return stop_time
    
    def timerLog(self, func_name, timerStart):
        
        timerStop = self.Timer.stop(timerStart)
        
        logText = "Query time (%s): %.4f sec" % (func_name, timerStop)
        
        timeColor = 2 if timerStop > 2 else (1 if timerStop > 1 else False) # if longer than 2 sec -> Warning, if longer than 1 sec -> Warning,
       
        if timeColor == 1:
            
            self.log.warning(logText)
            
        elif timeColor == 2:
            
            self.log.warning(logText)
            
        else:
            
            self.log.debug(logText)
    
    def error_exit(self, message: str, is_error: bool = True):
        
        self.log.error(message)
        
        sys.exit(1)
    
    def create_table(self, table_name: str):

        table_object = self.get_table_by_name(table_name)

        table_object.create(bind = self.engine)

        self.log.warning("'%s' database -> '%s' table created." % (str(self.__dbName),str(table_name)))
   
    def initTables(self):

        self.log.debug("Mysql init tables")

        for table_name in dict(self.tableBase.metadata.tables).copy().keys():

            self.log.debug("Mysql init '%s' table" % (str(table_name)))

            self.initTable(table_name, auto_create_table = self.autoCreateTables)
            
    def initTable(self, table_name: str, auto_create_table: bool = False):

        inspector = inspect(self.engine)

        db_tables = inspector.get_table_names()

        if table_name not in db_tables:
            
            if auto_create_table == True:
                
                self.create_table(table_name)
                
            else:
                raise Exception("'%s' database -> '%s' table does not exist." % (str(self.__dbName),str(table_name)))
       
        else:
           
            self.check_and_add_columns(inspector, table_name)
            
    def mysqlVersionCheck(self, minMysqlVersion):

        result = None

        with self.engine.connect() as conn:

            res = conn.execute(select(func.version()))
   
            result = res.fetchone()

        mysqlVersion = None
        
        if result is not None:
            
            mysqlVersion = result[0]
            versionStatus, serVersion = self.versionCheck(mysqlVersion, minMysqlVersion)

            if versionStatus:
                
                self.log.debug("'%s' database -> Mysql Version: %s" % (str(self.__dbName),str(serVersion)))
                
                return True
           
            else:
               
                self.error_exit("'%s' database -> Mysql VERSION is older than required! -> Current='%s'; MinRequired='%s'" % (str(self.__dbName), str(mysqlVersion), str(minMysqlVersion)), is_error = True)
       
        else:
           
            self.error_exit("'%s' database -> Mysql VERSION not found!" % (str(self.__dbName)), is_error=True)
    
    def versionCheck(self, current, required):
        
        ser_required_version = self.serVersion(required)
        ser_current_version = self.serVersion(current)

        ver_status = True
        
        if ser_current_version[2] < ser_required_version[2]:
            
            ver_status = False
            
            if ser_current_version[1] > ser_required_version[1]:
                
                ver_status = True
                
                if ser_current_version[0] < ser_required_version[0]:
                    
                    ver_status = False
                    
                else:
                    
                    ver_status = True
       
        else:
          
            if ser_current_version[1] == ser_required_version[1]:
                
                ver_status = True
                
                if ser_current_version[0] < ser_required_version[0]:
                    
                    ver_status = False
                    
                else:
                    
                    ver_status = True

        return ver_status, str('.'.join([str(int) for int in ser_current_version]))
    
    def serVersion(self, strVersion):
        
        try:
           
            pre_split =  strVersion.split('-')
           
            version_list = pre_split[0].split('.')
      
        except:
           
            version_list = strVersion.split('.')

        ver = []
       
        for item in version_list:
           
            try:
           
                ver.append(int(item))
           
            except:
           
                return ver
       
        return ver
    
    def setupTables(self):

        # print(vars(self.tableBase.metadata))

        for table_name, table_object in self.tableBase.metadata.tables.items():

            self.setupTable(table_name, table_object)

    def setupTable(self, table_name: str, table_object: object):

        if hasattr(self.tables, str(table_name)) == False:

            # print(vars(table_object))

            if self.sqlType == "mysql":
                if hasattr(table_object, "dialect_options") == True:
                    if 'mysql' in table_object.dialect_options:

                        if 'engine' not in table_object.dialect_options['mysql']._non_defaults and self.mysql_engine is not None:
                            table_object.dialect_options['mysql']._non_defaults['engine'] = self.mysql_engine

                        if 'charset' not in table_object.dialect_options['mysql']._non_defaults and self.mysql_charset is not None:
                            table_object.dialect_options['mysql']._non_defaults['charset'] = self.mysql_charset
                            
                    elif 'mysql' not in table_object.dialect_options:
                        table_object.dialect_options['mysql'] = sql.base._DialectPricegDict()

                        table_object.dialect_options['mysql']._non_defaults['engine'] = self.mysql_engine

                        table_object.dialect_options['mysql']._non_defaults['charset'] = self.mysql_charset

            if str(table_name) in self.tables_metaclasses:

                setattr(self.tables, str(table_name), self.tables_metaclasses[str(table_name)])

            else:
                
                raise Exception("table name '%s' not found in tables_metaclasses" % (str(table_name)))

        else:

            self.log.warning("Already exist table name '%s'" % (str(table_name)))

    def get_table_by_name(self, table_name: str):

        for _table_name, _table_object in self.tableBase.metadata.tables.items(): 

            if _table_name == table_name:

                return _table_object
        
        return None

    def add_column(self, table_name: str, column: Column):
        """
        {
        'key': 'password', 
        'name': 'password', 
        'table': Table(
          'users', 
          MetaData(), 
          Column('id', BigInteger(), table=<users>, primary_key=True, nullable=False), 
          Column('username', VARCHAR(length=250), table=<users>, nullable=False, comment='Username'),
          Column('password', VARCHAR(length=250), table=<users>, nullable=False, comment='Password'), 
          schema=None
          ), 
        'type': VARCHAR(length=250), 
        'is_literal': False, 
        'primary_key': False, 
        '_insert_sentinel': False, 
        '_omit_from_statements': False, 
        '_user_defined_nullable': False, 
        'nullable': False, 
        'index': None, 
        'unique': None, 
        'system': False, 
        'doc': None, 
        'autoincrement': 'auto', 
        'constraints': set(), 
        'foreign_keys': set(), 
        'comment': 'Password', 
        'computed': None, 
        'identity': None, 
        'default': None, 
        'onupdate': None, 
        'server_default': None, 
        'server_onupdate': None, 
        '_creation_order': 704, 
        'dispatch': <sqlalchemy.event.base.DDLEventsDispatch object at 0x000001B0B6074D40>, 
        '_proxies': [], 
        'proxy_set': frozenset(
            {Column('password', VARCHAR(length=250), table=<users>, nullable=False, comment='Password')
            })}
        """
        # print(vars(column))

        try:
            
            with self.engine.connect() as conn:
                
                query = 'ALTER TABLE %s ADD COLUMN %s ' % (str(table_name), str(column.name))

                # ENUM handling
                if isinstance(column.type, Enum):
                    
                    enum_values = "', '".join(column.type.enums)
                    query += "ENUM('%s')" % enum_values
               
                else:
                    
                    query += str(column.type)

                if column.nullable == False:
                   
                    query += " NOT NULL"

                if column.autoincrement == True:
                  
                    query += " AUTO_INCREMENT"

                if column.primary_key == True:
                   
                    query += " PRIMARY KEY"

                if column.default is not None:
                  
                    query += " DEFAULT"
                   
                    if isinstance(column.default.arg, str):
                     
                        query += " '%s'" % (str(column.default.arg))
                  
                    else:
                      
                        query += " %s" % (str(column.default.arg))

                if column.comment is not None:
                   
                    query += " COMMENT '%s'" % (str(column.comment))
                
                query += ";"
                
                conn.execute(text(query))
                
                self.log.warning("'%s' database -> '%s' column added to '%s' table" % (str(self.__dbName), str(column.name), str(table_name)))
       
        except OperationalError as e:
           
            self.error_exit("'%s' database -> Failed to add '%s' column to '%s' table: %s" % (str(self.__dbName), str(column.name), str(table_name), str(e)), is_error=True)

    def check_and_add_columns(self, inspector: Inspector, table_name: str):
        # Use inspector to get columns from the actual database table
        
        table_class = self.get_table_by_name(table_name)

        table_columns = inspector.get_columns(table_name)

        primary_key_constraint = inspector.get_pk_constraint(table_name)

        actual_columns = [col['name'] for col in table_columns]

        # Check if columns in table class exist in actual database table and add them if they don’t
        for column in table_class.columns:
            # print(vars(column))

            column: Column

            if column.name not in actual_columns:

                if self.autoAddNewColumns == True:
                   
                    self.log.warning("'%s' database -> '%s' column  does not exist in '%s' table. Adding it" % (str(self.__dbName), str(column.name),str(table_name)))

                    self.add_column(table_name, column)
                
                else:
                    
                    self.error_exit("'%s' database -> '%s' column does not exist in '%s' table" % (str(self.__dbName),str(column.name),str(table_name)), is_error=True)

            else:

                if self.checkColumnParameters == True:

                    self.check_column_parametes(table_name, table_columns, primary_key_constraint, column, error_exit = True)

    def get_actual_database_table_colum(self, table_columns, primary_key_constraint, column_name: str):

        for actual_col in table_columns:

            if actual_col['name'] == column_name:

                actual_col['is_primary_key'] = next((True for pk_col in primary_key_constraint['constrained_columns'] if pk_col == column_name), False)
                
                return actual_col

        return None

    def check_column_parametes(self, table_name, table_columns, primary_key_constraint, column: Column, error_exit = False):

        if error_exit:
            
            error_func = self.error_exit
            kwargs = {'is_error': True}
            
        else:
            
            error_func = self.log.error
            kwargs = {}
        
        actual_database_column = self.get_actual_database_table_colum(table_columns, primary_key_constraint, column.name)

        if actual_database_column is not None:

            #actual database column: 
            # {'name': 'process_name', 'type': VARCHAR(length=200), 'default': None, 'comment': None, 'nullable': True}
            # {'name': 'line_no', 'type': INTEGER(), 'default': None, 'comment': None, 'nullable': True, 'autoincrement': False}

            # BEGIN type

            actual_database_column_type_splited = str(actual_database_column['type']).split(" ")
         
            actual_database_column_type = actual_database_column_type_splited[0]
    
            if str(column.type).lower() == "BOOLEAN".lower():
                
                if str(actual_database_column_type).lower() == "TINYINT".lower() or  str(actual_database_column_type).lower() == "SMALLINT".lower():
                   
                    actual_database_column_type = str(column.type)

            if "VARCHAR" in str(actual_database_column_type):
               
                actual_database_column_type = actual_database_column['type']

            if "CHAR" in str(actual_database_column_type):
               
                actual_database_column_type = actual_database_column['type']
                
            if "DECIMAL" in str(actual_database_column_type):
                
                actual_database_column_type = actual_database_column['type']

            # if str(column.type) != str(actual_database_column_type):
            if str(column.type) not in str(actual_database_column_type):

                self.log.debug("'%s' table -> '%s' actual database column: %s" % (str(table_name), str(actual_database_column['name']),str(actual_database_column)))

                self.log.debug("'%s' table -> '%s' definied column: %s" % (str(table_name), str(column.name), str(vars(column))))

                error_func("'%s' database -> '%s' table -> '%s' colum -> Defined colum type ('%s') and actual database column type ('%s') do not match!" % (
                    str(self.__dbName),
                    str(table_name),
                    str(column.name), 
                    str(column.type),
                    str(actual_database_column_type),
                    ), 
                    **kwargs
                    )
                
            # END type

            # BEGIN type

            if column.nullable != actual_database_column['nullable']:

                error_func("'%s' database -> '%s' table -> '%s' colum -> Defined colum nullable (%s) and actual database column nullable (%s) do not match!" % (
                    str(self.__dbName),
                    str(table_name),
                    str(column.name), 
                    str(column.nullable),
                    str(actual_database_column['nullable']),
                    ), 
                    **kwargs
                    )

            # END type

            # BEGIN primary_key

            if column.primary_key != actual_database_column['is_primary_key']:

                error_func("'%s' database -> '%s' table -> '%s' colum -> Defined colum primary_key (%s) and actual database column primary_key (%s) do not match!" % (
                    str(self.__dbName),
                    str(table_name),
                    str(column.name), 
                    str(column.primary_key),
                    str(actual_database_column['is_primary_key']),
                    ), 
                    **kwargs
                    )

            # END primary_key

            # BEGIN autoincrement

            if 'autoincrement' not in actual_database_column or actual_database_column['autoincrement'] == False:

                actual_database_column['autoincrement'] = 'auto'

            if column.autoincrement != actual_database_column['autoincrement']:

                error_func("'%s' database -> '%s' table -> '%s' colum -> Defined colum autoincrement (%s) and actual database column autoincrement (%s) do not match!" % (
                    str(self.__dbName),
                    str(table_name),
                    str(column.name), 
                    str(True if column.autoincrement == True else False),
                    str(True if actual_database_column['autoincrement'] == True else False),
                    ), 
                    **kwargs
                )
                    
            # END autoincrement
    
    def declarative_base(db_name, **kwags):

        if db_name in Tables:
            
            raise Exception("Already exist db name: %s" % (str(db_name)))
        
        else:
            
            Tables[str(db_name)] = {}

        class DeclarativeMeta(DefaultDeclarativeMeta):
            
            def __init__(cls, classname: str, bases: tuple[type[object], ...], dict_: dict[str, object], **kw: object) -> None:

                if cls.__module__ != "sqlalchemy.orm.decl_api":

                    if classname not in Tables[str(db_name)]:

                        if "__tablename__" not in dict_:

                            dict_["__tablename__"] = str(classname)
                        
                        cls.__tablename__ = str(classname)

                        # print(classname, bases, dict_, kw)

                        Tables[str(db_name)][str(classname)] = cls
                        
                else:
                    
                    if classname not in Tables[str(db_name)]:
                        
                        Tables[str(db_name)]["base"] = cls

                super().__init__(classname, bases, dict_, **kw)

        if "metaclass" not in kwags:
            
            kwags['metaclass'] = DeclarativeMeta

        kwags['name'] = db_name

        return default_declarative_base(**kwags)
    
    def createMysqlDB(self):
        
        if self.autoCreateDB == True:
            
            create_database(self.engine.url, self.encoding)

            if not database_exists(self.async_engine.url):
                
                self.error_exit("Can't create mysql db: '%s'!" % (str(self.__dbName)), is_error = True)
                
            else:
                
                self.log.warning("Mysql database created: %s" % (str(self.__dbName)))
                
        else:
            
            self.error_exit("Not found mysql db: '%s'!" % (str(self.__dbName)), is_error = True)
            
    def checkMysqlExist(self):
        
        if not database_exists(self.engine.url):
            
            self.log.error("Mysql database not found: {0}".format(self.__dbName))

            self.createMysqlDB()

    def enableGeneralLog(self):

        # RESET:
        # SET GLOBAL log_bin_trust_function_creators=0;
        # SET GLOBAL log_output = 'file';
        # SET GLOBAL general_log = 0;

        # SELECT:
        # SELECT event_time, user_host, thread_id, server_id, command_type, argument, CONVERT(argument USING utf8) AS query_string 
        # FROM mysql.general_log 
        # WHERE CONVERT(argument USING utf8) LIKE '%TABLENAME%' ORDER BY event_time DESC;

        with self.engine.connect() as conn:
            # # Enable the creation of stored functions and procedures by users who do not have the SUPER privilege
            result = conn.execute(text("SELECT @@log_bin_trust_function_creators")).fetchone()

            if len(result) > 0 and result[0] != 1:
                
                self.log.warning("Enable Global log -> Enable the creation of stored functions and procedures by users who do not have the SUPER privilege -> SET GLOBAL log_bin_trust_function_creators = 1;")
               
                conn.execute(text("SET GLOBAL log_bin_trust_function_creators=1;"))
                conn.commit()

            # Set the logging output format to TABLE
            result = conn.execute(text("SELECT @@log_output")).fetchone()

            if len(result) > 0 and result[0] != "TABLE":
                
                self.log.warning("Enable Global log -> Set the logging output format to TABLE -> SET GLOBAL log_output = 'TABLE';")

                conn.execute(text("SET GLOBAL log_output = 'TABLE';"))
                conn.commit()

            # Enable the general query log
            result = conn.execute(text("SELECT @@general_log")).fetchone()

            if len(result) > 0 and result[0] != 1:
               
                self.log.warning("Enable Global log -> Enable the general query log -> SET GLOBAL general_log = 1;")

            conn.execute(text("SET GLOBAL general_log = 1;"))
            conn.commit()
    
    async def connect_database(self, 
        user, password, 
        host, port, 
        db_name,
        sshtunnel_host: str = None,
        sshtunnel_port: int = None,
        sshtunnel_user: str = None,
        sshtunnel_pass: str = None,
        sshtunnel_private_key_path: str = None,
        db_size_check: bool = False,
        minMysqlVersion: str = "8.0.29"
        ):
        
        self.minMysqlVersion = minMysqlVersion
        
        self.__dbName = db_name
        
        if self.async_engine is not None:
            
            self.log.warning("connect_database() called more than once; skipping")
            
            return

        if sshtunnel_host is not None and sshtunnel_port is not None:
            
            db_host = "127.0.0.1"

            self.ssh_tunnel = SSHTunnel(
                name = f"MySQL-{self.__dbName}",
                ssh_host = sshtunnel_host,
                ssh_port = sshtunnel_port,
                ssh_user = sshtunnel_user,
                ssh_pass = sshtunnel_pass,
                ssh_private_key_ppk_path = sshtunnel_private_key_path,
                sql_hostname = host,
                sql_port = port,
            )

            self.ssh_tunnel_reconnect_service = SSHTunnelReconnectService(tunnel = self.ssh_tunnel)

            SSHTunnelConnections.add_connection(SSHTunnelConnection(ssh_tunnel = self.ssh_tunnel))
            
            self.ssh_tunnel_reconnect_service.start()

            port = self.ssh_tunnel_reconnect_service.local_bind_port
            
            host = db_host

            self.log.debug("DB with SSH tunnel -> Name: %s, Host: %s, Port: %s, User: %s, Password: %s" % (
                self.__dbName,
                host,
                port,
                user,
                String.maskString(password, perc = 1)
            ))
            
        else:
            
            self.log.debug("DB direct -> Name: %s, Host: %s, Port: %s, User: %s, Password: %s" % (
                self.__dbName,
                host,
                port,
                user,
                String.maskString(password, perc = 1)
            ))

        self.sync_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{self.__dbName}"
    
        self.engine = create_engine(self.sync_url, **self.create_engine_extra_kwargs)
        
        self.log.info("Sync engine connected...")
    
        self.setupTables()
        
        self.checkMysqlExist()
        
        if self.general_log == True:

            self.enableGeneralLog()
        
        self.initTables() 
        
        if db_size_check == True:

            totalSizeKB, tablesSizeKB = self.getDbSize()

            self.log.debug("'%s' database size: %s" % (str(self.__dbName),str(self.DbSizeFormatter(totalSizeKB))))

            for table, size in tablesSizeKB.items():
                
                self.log.debug("'%s' -> '%s' table size: %s" % (str(self.__dbName), str(table),str(self.DbSizeFormatter(size))))
        
        self.mysqlVersionCheck(minMysqlVersion)
        
        self.import_queries()
        
        if self.session_enabled == True:
            
            self.Session: Session = SessionMaker(
                parent = self, 
                bind = self.engine, 
                class_ = Session, 
                **self.async_sessionmaker_extra_kwargs
            )
        
        if self.__set_async_engine == True:

            self.async_url = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{self.__dbName}"

            self.async_engine = create_async_engine(self.async_url, echo = True, **self.async_create_engine_extra_kwargs)

            self.log.info("Async engine connected...")
            
            if self.session_enabled == True:
                
                self.AsyncSession: AsyncSession = AsyncSessionMaker(
                    parent = self,
                    bind = self.async_engine,
                    class_ = AsyncSession,
                    expire_on_commit = False,
                )
        
        self.__query_references_check(
            queries = queries, 
            query_callback = AsyncQueryCallback
        )

    def DbSizeFormatter(self, size_in_kb):
        
        if size_in_kb is not None:
            
            if size_in_kb > 1024:
                
                size_in_mb = size_in_kb / 1024
                
                if size_in_mb > 1024:
                    
                    size_in_gb = size_in_mb / 1024
                    
                    return "%.2f GB" % size_in_gb
                
                else:
                    
                    return "%.2f MB" % size_in_mb
                
            else:
                
                return "%.2f KB" % size_in_kb
            
        else:
            
            return "N/D"

    def getDbSize(self):

        tables = {}
        
        for table_name, table_object in self.tableBase.metadata.tables.items():
            
            tables[table_name] = {}
            tables[table_name]['object'] = table_object
            tables[table_name]['columns'] = [column.name for column in inspect(table_object).c]

        # print(tables)

        tablesSizeKB = {}

        for tableName, table_item in tables.items():
            
            table = table_item['object']

            result = []

            columns = [getattr(table.c, column) for column in table_item['columns']]

            # print(columns)

            my_select = select(*[func.char_length(column) for column in columns])
            
            with self.engine.connect() as conn:

                res = conn.execute(my_select)
                
                result = res.fetchall()

            # print(result)

            newResults = []
            
            for items in result:
                
                newItems = []
                
                for value in items:
                    
                    if value is not None:
                        
                        newItems.append(value)

                if len(newItems) > 0:
                    
                    newResults.append(newItems)

            # print(newResults)
            tablesSizeKB[tableName] = sum(sum(i) for i in zip(*newResults)) / 1024 if result is not None else 0
           
            res.close()

        totalSizeKB = sum([size for table, size in tablesSizeKB.items()])

        # statement = """
        #     SELECT
        #     SUM(ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024), 2)) AS "SIZE IN MB"
        #     FROM information_schema.TABLES
        #     WHERE
        #     TABLE_SCHEMA = '%s';
        # """ % str(self.__dbName)

        # res = self.informationSchemaEngine.execute(statement)
        # result = res.fetchone()
        # res.close()

        # if len(result) > 0 and result[0] is not None:
        #     size_in_kb = result [0]
        # else:
        #     size_in_kb = None
        # print(totalSizeKB, tablesSizeKB)
        
        return totalSizeKB, tablesSizeKB
    
    # async def init_db(self):
        
    #     if self.engine is None:
            
    #         self.log.error("init_db() called but database not connected")
            
    #         raise RuntimeError("Database not connected. Call `connect_database()` first.")
        
    #     async with self.engine.begin() as conn:
            
    #         await conn.run_sync(Base.metadata.create_all)
            
    #         self.log.info("Database schema initialized successfully")
        
    def __query_references_check(self, queries: ModuleType, query_callback: AsyncQueryCallback):

        if isinstance(queries, ModuleType):

            queries_init_path = os.path.join(self.queries_path, '__init__.py')
            
            for name in dir(queries):

                existing_query = getattr(queries, str(name))

                if insp.isfunction(existing_query) == True:

                    if str(name) not in dir(self.queries):

                        self.log.error("\n\n'%s' query reference does not exist in imported queries. Please delete it from: '%s'\n" % (
                            str(name),
                            str(queries_init_path)
                        ))

            for query_name in dir(self.queries):

                if not query_name.startswith("_"):

                    query_callback = getattr(self.queries, str(query_name))

                    query_file_name = insp.getfile(query_callback.query_attr.query)
                    # print(query_file_name)
                    
                    type_hints =  typing.get_type_hints(query_callback.query_attr.query)

                    return_type = type_hints.get('return')

                    if return_type == types.NoneType:
                        
                        return_type = "None"
                        
                    elif insp.isclass(return_type):
                        
                        return_type = return_type.__name__

                    if hasattr(queries, query_name) == False:
                        
                        signature = insp.signature(query_callback.query_attr.query)

                        iscoroutinefunction = insp.iscoroutinefunction(query_callback.query_attr.query)

                        kwargs_str_list = []

                        for name, param in signature.parameters.items():

                            kwargs_str = ""

                            param_annotations = []

                            param_annotation_names = []

                            if not hasattr(param.annotation, '__name__') and isinstance(param.annotation, types.UnionType):
                                
                                for item in typing.get_args(param.annotation):

                                    param_annotations.append(item)
                                    param_annotation_names.append(item.__name__)

                            if hasattr(param.annotation, '__name__') or len(param_annotations) > 0 :

                                if len(param_annotations) == 0:

                                    param_type = param.annotation

                                    param_type_name = param_type.__name__

                                    # is_builtin_type = param_type_name in dir(builtins)

                                else:

                                    param_type_name = ' | '.join(param_annotation_names)

                                    # is_builtin_type = next((False for param_type in param_annotations if param_type not in dir(builtins)), True)

                                if str(name) != 'self':

                                    # print(dir(param))

                                    # print("name: %s type: %s, default: %s, empty: %s" % (
                                    #     str(name), 
                                    #     str(param_type_name), 
                                    #     str(param.default.__name__), 
                                    #     str(param.empty)
                                    #     ))

                                    kwargs_str = "%s%s" % (
                                        str(name),
                                        # str(": %s" % (str(param_type_name)) if is_builtin_type else "")
                                        str(": %s" % (str(param_type_name)))
                                    )

                                    kwargs_str_list.append(kwargs_str)
                            
                        func_str = "\n%sdef %s(%s)%s: pass" % (
                            str("async " if iscoroutinefunction == True else ""),
                            str(query_name), 
                            str(', '.join(kwargs_str_list)),
                            str(" -> %s" % (str(return_type)) if return_type is not None else "")
                            )
                        
                        self.log.error("\n\n'%s' query reference not found in '%s'.\nPlease add this: %s\n" % (
                            str(query_name),
                            str(queries_init_path),
                            str(func_str),
                        ))

                    setattr(queries, query_name, query_callback)

    def import_queries(self):

        # package_dir = Path(__file__).resolve().parent

        queries_count = 0

        if self.queries_path is not None:
            
            package_dirs = [x[0] for x in os.walk(self.queries_path)]

            for i, package_dir in enumerate(package_dirs):

                for (_, module_name, _) in iter_modules([package_dir]):

                    if module_name is not None:
                        # import the module and iterate through its attributes
                        # module = import_module(f"{__name__}.{module_name}")

                        # print(module_name)

                        package_files = os.listdir(package_dir)

                        pyd_file = False
                        
                        pyd_file_name = None

                        for file in package_files:
                            
                            if os.path.basename(file).endswith(".pyd") and os.path.basename(os.path.splitext(file)[0]).split(".")[0] == module_name and self.getOS() == "windows":
                                # print("basename:",os.path.basename(file))
                                # print("splitext:",os.path.basename(os.path.splitext(file)[0]).split(".")[0])
                                pyd_file = True
                                pyd_file_name = file

                        if pyd_file == True:

                            full_path = os.path.join(package_dir, pyd_file_name)

                        else:
                        
                            filename = module_name + ".py"
                            full_path = os.path.join(package_dir,filename)

                        # module = SourceFileLoader(module_name,full_path).load_module()

                        # print(full_path, module_name)

                        module = pylibimport.import_module(full_path, import_chain = module_name, reset_modules = True)

                        for attribute_name in dir(module):
                            
                            if not attribute_name.startswith("_"):
                                
                                attribute = getattr(module, attribute_name)

                                if insp.isfunction(attribute) or str(type(attribute)) == "<class 'cython_function_or_method'>" \
                                    or QueryBase in self.__get_all_subclasses(attribute) or AsyncQueryBase in self.__get_all_subclasses(attribute):
                                    
                                # if callable(attribute) and module_name == Path(getfile(attribute)).stem:   
                                    if attribute.__name__ == module_name or attribute.__module__ == module_name:
                                        
                                        if callable(attribute):   
                                                
                                            # print(module_name, attribute.__name__) 

                                            if QueryBase in self.__get_all_subclasses(attribute):

                                                # Test
                                                # print(attribute)
                                                attribute(db = self)

                                                setattr(self.queries, attribute.__name__,  QueryCallback(db = self, query_attr = attribute))
                                            # else:
                                            #     setattr(self.queries, attribute.__name__, attribute)

                                                self.log.debug("Import '%s' query from: %s" % (str(attribute.__name__),str(full_path)))

                                                queries_count += 1
                                                
                                            # Add the class to this package's variables
                                            if AsyncQueryBase in self.__get_all_subclasses(attribute):
                                                
                                                self.__set_async_engine = True
                                                    
                                                # Test
                                                # print(attribute)
                                                attribute(db = self)

                                                setattr(self.queries, attribute.__name__,  AsyncQueryCallback(db = self, query_attr = attribute))
                                            # else:
                                            #     setattr(self.queries, attribute.__name__, attribute)

                                                self.log.debug("Import '%s' async query from: %s" % (str(attribute.__name__),str(full_path)))

                                                queries_count += 1

                                            # vars()[attribute.__name__] = attribute
        
        if self.queries_path is None:
            
            self.log.warning("Queries path is None. Import disabled!")
            
        elif queries_count == 0:
            
            self.log.warning("0 query found in queries path: %s" % (str(self.queries_path)))

    def __get_all_subclasses(self, class_attr):
        
        all_subclasses = []

        if insp.isclass(class_attr):

            for subclass in class_attr.__bases__:
                
                all_subclasses.append(subclass)
                
                all_subclasses.extend(self.__get_all_subclasses(subclass))

        # print(all_subclasses)

        return all_subclasses

class Queries:
    def __init__(self):
        pass
