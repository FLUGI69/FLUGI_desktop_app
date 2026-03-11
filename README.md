<div align="center">

# FLUGI Desktop App

Desktop application for managing boat works and attachments.

</div>

<div align="center">
	<h3>Portfolio Reference Project</h3>
	<p>
		Desktop business-management application built with <b>Python + PyQt6</b>,
		asynchronous services, database integration, Redis cache, WebSocket sync,
		and HTML/PDF document rendering.
	</p>
</div>

<hr>

## Project Overview

FLUGI Desktop App is a modular desktop system focused on real operational workflows:

- interactive multi-view desktop UI (`PyQt6`)
- asynchronous app lifecycle (`qasync`, `asyncio`)
- MySQL data layer with query modules and session helpers
- Redis-backed caching and refresh mechanisms
- optional WebSocket client integration for real-time updates
- background workers for reminders and rental-end checks
- Jinja2 HTML templates for document generation
- launcher/update flow and packaging support (`PyInstaller`)

This repository is used as a **portfolio project reference**, showing a full-stack desktop architecture around Python.

## Tech Stack

<table>
	<tr><th>Area</th><th>Technology</th></tr>
	<tr><td>Language</td><td>Python 3.13.3</td></tr>
	<tr><td>Desktop UI</td><td>PyQt6, PyQt6-WebEngine</td></tr>
	<tr><td>Async Runtime</td><td>asyncio, qasync</td></tr>
	<tr><td>Database</td><td>MySQL, SQLAlchemy (sync + async patterns)</td></tr>
	<tr><td>Cache / Messaging</td><td>Redis, python-socketio</td></tr>
	<tr><td>Templates / Docs</td><td>Jinja2, HTML templates, WeasyPrint</td></tr>
	<tr><td>Automation / External</td><td>Playwright, Google APIs, OpenAI SDK</td></tr>
	<tr><td>Packaging</td><td>PyInstaller (`flugi_app.spec`)</td></tr>
</table>

## Complete Technology Stack & Libraries

### Desktop UI & Graphics
- **PyQt6** (6.9.0) — GUI framework
- **PyQt6-WebEngine** (6.9.0) — embedded web browser engine
- **Pillow** (11.3.0) — image processing and manipulation
- **qasync** (0.28.0) — Qt + asyncio event loop integration

### Database & ORM
- **SQLAlchemy** (2.0.41) — SQL toolkit and ORM
- **SQLAlchemy-Utils** (0.41.2) — additional utilities for SQLAlchemy
- **aiomysql** (0.2.0) — async MySQL driver
- **PyMySQL** (1.1.1) — Pure Python MySQL client

### Cache & Real-time Communication
- **redis** (5.0.4) — Redis client
- **python-socketio** (5.13.0) — WebSocket/Socket.IO client
- **python-engineio** (4.12.2) — Engine.IO protocol implementation
- **websocket-client** (1.9.0) — WebSocket client library
- **websockets** (15.0.1) — async WebSocket implementation

### HTTP & Network
- **requests** (2.32.3) — HTTP library
- **httpx** (0.28.1) — modern async HTTP client
- **httpcore** (1.0.9) — low-level HTTP transport
- **aiohttp** (3.12.0) — async HTTP client/server framework
- **aiofiles** (24.1.0) — async file I/O
- **urllib3** (2.5.0) — HTTP client with connection pooling
- **paramiko** (3.5.1) — SSH protocol implementation
- **sshtunnel** (0.4.0) — SSH tunneling utility

### Web Automation & Scraping
- **playwright** (1.55.0) — browser automation framework
- **selenium-stealth** (1.0.6) — Selenium detection avoidance
- **beautifulsoup4** (4.13.4) — HTML/XML parser
- **lxml** (5.4.0) — fast XML/HTML processing

### Document Generation & PDF
- **WeasyPrint** (68.0) — HTML to PDF converter
- **CairoSVG** (2.8.2) — SVG converter
- **PyMuPDF** (1.26.1) — PDF toolkit (fitz)
- **Jinja2** (3.1.6) — template engine
- **reportlab** capabilities via WeasyPrint
- **qrcode** (8.2) — QR code generation

### Data Processing & Scientific Computing
- **pandas** (2.3.0) — data analysis and manipulation
- **numpy** (2.3.1) — numerical computing
- **scipy** (1.16.0) — scientific computing
- **narwhals** (2.12.0) — DataFrame interoperability layer

### Google Integration
- **google-api-python-client** (2.169.0) — Google APIs client
- **google-auth** (2.40.1) — Google authentication
- **google-auth-httplib2** (0.2.0) — HTTP transport for Google Auth
- **google-auth-oauthlib** (1.2.2) — OAuth 2.0 integration
- **googleapis-common-protos** (1.70.0) — Common protocol buffers

### AI & Machine Learning
- **openai** (1.90.0) — OpenAI API client (GPT integration)

### Financial & External APIs
- **mnb** (1.0.1) — Magyar Nemzeti Bank (Hungarian National Bank) exchange rate API
- **zeep** (4.3.2) — SOAP client for web services

### Security & Cryptography
- **bcrypt** (4.3.0) — password hashing
- **cryptography** (46.0.3) — cryptographic recipes and primitives
- **pyOpenSSL** (25.3.0) — OpenSSL wrapper

### Data Validation & Serialization
- **pydantic** (2.11.4) — data validation using Python type hints
- **pydantic_core** (2.33.2) — core validation logic for Pydantic
- **attrs** (25.3.0) — classes without boilerplate

### Logging & Development Tools
- **colorlog** (6.9.0) — colored terminal logging
- **colorama** (0.4.6) — cross-platform colored terminal output
- **logging** (built-in) — structured logging framework

### Configuration & Utilities
- **configobj** (5.0.9) — config file reader/writer
- **configparser** (7.2.0) — configuration file parser
- **python-dateutil** (2.9.0.post0) — date/time parsing and manipulation
- **pytz** (2025.2) — timezone definitions
- **tzdata** (2025.2) — timezone database

### Medical Imaging (Nibabel/Nipype)
- **nibabel** (5.3.2) — neuroimaging data I/O
- **nipype** (1.10.0) — neuroimaging pipeline framework
- **prov** (2.0.2) — provenance data model
- **etelemetry** (0.3.1) — anonymous usage tracking
- **traits** (7.0.2) — typed attributes for Python

### Async & Concurrency
- **trio** (0.31.0) — async I/O framework
- **trio-websocket** (0.12.2) — WebSocket library for Trio
- **outcome** (1.3.0.post0) — capture function outcomes
- **sniffio** (1.3.1) — async library detection
- **greenlet** (3.2.2) — lightweight concurrent programming

### Compression & Encoding
- **Brotli** (1.1.0) — compression algorithm
- **zstandard** (0.25.0) — Zstandard compression
- **zopfli** (0.2.3.post1) — compression library

### Build & Packaging
- **PyInstaller** (6.14.2) — freeze Python applications
- **pyinstaller-hooks-contrib** (2025.5) — extra PyInstaller hooks
- **setuptools** (80.8.0) — package development utilities
- **altgraph** (0.17.4) — graph library for PyInstaller
- **pefile** (2023.2.7) — PE file parser (Windows executables)

### Miscellaneous
- **click** (8.2.1) — command-line interface framework
- **rich** (14.0.0) — rich text and formatting in terminal
- **tqdm** (4.67.1) — progress bar utilities
- **bidict** (0.23.1) — bidirectional dictionary
- **cachetools** (5.5.2) — caching utilities
- **simplejson** (3.20.1) — JSON encoder/decoder
- **sortedcontainers** (2.4.0) — sorted collections
- **defusedxml** (0.7.1) — XML bomb protection
- **looseversion** (1.3.0) — version comparison
- **packaging** (25.0) — package version handling

## Repository Structure

Key directories and responsibilities:

- `gui/__main__.py`
	- Main entry point.
	- Applies runtime patches, validates config references, creates the Qt application, and starts interfaces.
- `gui/interfaces/`
	- Startup orchestration, stylesheet loading, DB/Redis setup, lifecycle callback registration.
- `gui/async_loop/qt_app.py`
	- Core application runtime container.
	- Bridges Qt event loop with asyncio.
	- Registers startup/shutdown callbacks and manages background tasks.
- `gui/view/`
	- UI screens, main window, modal components, admin views, table-related views.
- `gui/launcher/launcher.py`
	- Startup launcher and update-check flow (dev vs packaged behavior).
- `gui/db/`
	- MySQL connection layer, sessions, query framework, redis helpers, tunnel/network support.
- `gui/services/`
	- Background workers and service-level cache helpers.
- `gui/utils/`
	- Logger mixin, helper modules, event handlers, enums, dataclass-like models (`utils/dc`).
- `gui/dataclass/base.py`
	- Base model utilities (serialization, enum conversion, websocket model discovery).
- `gui/templates/`
	- HTML templates such as `price_quotation.html` and `redirect.html`.
- `flugi_app.spec`
	- Build configuration for PyInstaller packaging.

## Architecture Summary

### 1. Application Bootstrap

Start path:

1. `gui/__main__.py`
2. `Init.monkey_patch()` (Windows/qasync runtime stability patches)
3. `Init.config_reference_check()` (compares `config.py` to `config_example.py`)
4. `Init.pyqt_application()`
5. `Interfaces.run(qt_app)`

### 2. Runtime Container

`QtApplication` in `gui/async_loop/qt_app.py` is the central runtime object that owns:

- database client
- redis client
- websocket client (optional)
- reminder/rental workers
- template environment
- locks and tracked background tasks

### 3. Data and Services

- `gui/db/db.py`: custom MySQL wrapper with setup, table checks, query loading, and session abstractions.
- `gui/db/queries/`: query modules grouped by domain.
- `gui/services/backgound_tasks/`: async periodic workers (reminders and rentals).

#### Database Layer Deep Dive

**`declarative_base` and the Global `Tables` Dict**

The database architecture begins with a custom `declarative_base` factory that hooks into SQLAlchemy's metaclass system:

```python
TableBase = MySQLDatabase.declarative_base("example_db")
```

This call:
1. Creates a new entry in the global `Tables` dict with the database name `"example_db"` as the key.
2. Returns a custom `DeclarativeMeta`-based base class.
3. Every class that inherits from `TableBase` is automatically registered into `Tables["example_db"]` — the class name becomes the key, and the class itself becomes the value.

For example, in `gui/db/tables.py`:

```python
class example_db:

    class boat(TableBase):
        id = Column(BigInteger, autoincrement=True, primary_key=True)
        name = Column(String(255), nullable=False)
        ...

    class employee(TableBase):
        id = Column(BigInteger, autoincrement=True, primary_key=True)
        name = Column(String(100), nullable=False)
        ...
```

Each nested class (`boat`, `employee`, etc.) inherits from `TableBase`, which triggers the custom `DeclarativeMeta.__init__`. This automatically:
- Sets `__tablename__` to the class name (e.g., `"boat"`)
- Registers the class into `Tables["example_db"]["boat"]`, `Tables["example_db"]["employee"]`, etc.
- Stores the base class itself under `Tables["example_db"]["base"]`

**Startup Schema Validation (Sync Engine)**

When the application starts and calls `connect_database()`, the sync engine performs a full schema validation:

1. **`setupTables()`**: Iterates over `TableBase.metadata.tables` (the metadata dict containing all table definitions declared in Python). For each table, it matches the table name against the `tables_metaclasses` dict (extracted from the `example_db` class attributes). If a match is found, the table class is bound via `setattr` to the `tables` instance object.

2. **`checkMysqlExist()`**: Checks if the actual MySQL database exists. If not, and `auto_create_db=True`, it creates the database.

3. **`initTables()`**: For each table in the metadata dict:
   - Uses SQLAlchemy `Inspector` to get the list of tables that actually exist in the database.
   - **If a table is missing** and `auto_create_tables=True` → creates it automatically.
   - **If a table exists** → calls `check_and_add_columns()`:
     - Compares the columns defined in the Python model against the actual columns in the database.
     - **If a column is missing** and `auto_add_new_columns=True` → adds it with `ALTER TABLE`.
     - **If `check_column_parameters=True`** → additionally validates column type, nullable, primary key, and autoincrement between the model definition and the actual database column.

This means the database schema always stays in sync with the Python model definitions, without needing manual migrations.

**Query Module System (Runtime Import with Stubs)**

The query system uses a dynamic loading + stub verification pattern:

**1. `import_queries()` — Dynamic Scanning and Registration**

During `connect_database()`, after schema validation, `import_queries()` is called. It:

- Walks the entire `gui/db/queries/` directory (including subdirectories).
- For each `.py` file found, dynamically imports it using `pylibimport`.
- Inspects every attribute in the module.
- If an attribute is a class that inherits from `AsyncQueryBase`:
  - Instantiates it with `attribute(db=self)` to verify it works.
  - Wraps it in `AsyncQueryCallback(db=self, query_attr=attribute)`.
  - Registers it on the global `Queries` instance via `setattr(self.queries, attribute.__name__, ...)`.
  - Sets `__set_async_engine = True` → which triggers async engine creation.
- The same pattern applies for `QueryBase` (sync variant), wrapped in `QueryCallback`.

**Key constraint**: `attribute.__name__` (the class name) must match the module file name. This is enforced by the check `attribute.__name__ == module_name`.

**2. `__query_references_check()` — Stub Verification**

After all queries are imported, the system runs a reference check against the stubs in `gui/db/queries/__init__.py`:

- **For each stub function** defined in the `queries` module `__init__.py`: if it does not have a corresponding imported query on `self.queries`, an error is logged telling you to remove the orphaned stub.
- **For each imported query** on `self.queries`: if there is no matching stub function in `queries.__init__.py`, the system:
  - Inspects the query's `query()` method signature (parameter names, types, return type, async/sync).
  - Auto-generates the exact stub function signature.
  - Logs an error showing the exact code to add to `__init__.py`.
- Finally, it overwrites the stub with the real `AsyncQueryCallback` using `setattr(queries, query_name, query_callback)`. This is why at runtime `queries.select_tenant()` calls the actual query.

**3. Stubs in `gui/db/queries/__init__.py`**

The stubs look like regular async function signatures with `pass` body:

```python
async def select_tenant(item_id: int) -> None: pass
async def insert_boat_data(name: str, ship_id: int, ...) -> None: pass
```

These serve two purposes:
- **IDE support**: Provides autocomplete and type hints across the codebase.
- **Validation**: The system verifies that every imported query has a matching stub, and every stub has a matching query file.

**4. `AsyncQueryBase` and `AsyncQueryCallback`**

Each query file defines a class inheriting from `AsyncQueryBase`:

```python
class select_tenant(AsyncQueryBase):
    async def query(self, item_id: int) -> ...:
        # actual SQL logic here
```

The `AsyncQueryBase.__call__` method:
- Opens a new `AsyncSession` context.
- Calls `self.query(*args, **kwargs)` — the abstract method implemented by the derived class.
- Handles rollback on exceptions and logs session lifecycle.

`AsyncQueryCallback.__call__` wraps this:
- Creates a fresh instance of the query class: `query = self.query_attr(db=self.db)`
- Calls it: `return await query(*args, **kwargs)`

This means the full call chain is:
```
queries.select_tenant(item_id=5)
  → AsyncQueryCallback.__call__(item_id=5)
    → select_tenant(db=self.db)  # fresh instance
      → AsyncQueryBase.__call__(item_id=5)  # opens session
        → select_tenant.query(item_id=5)  # actual SQL
```

**Why This Architecture?**

- **Auto-schema sync**: Tables and columns are created/updated automatically — no manual migration scripts needed for development.
- **Convention enforcement**: File name must match class name; stubs must match queries. Violations are caught at startup with helpful error messages.
- **IDE integration**: Stubs in `__init__.py` give full autocomplete and type checking while the real implementation is loaded dynamically.
- **Fresh session per call**: Each query invocation gets its own session context with automatic rollback on failure.
- **Modular organization**: Queries are standalone files, grouped in subdirectories by domain.

### 4. UI Layer

- `gui/view/main_window.py` coordinates major app views and reminder-related interactions.
- UI components are split into logical submodules (`admin`, `elements`, `modal`, `tables`, etc.).

### 5. Real-time and Cache

- `gui/websocket/ws_client.py` auto-registers async event handlers and processes structured websocket messages.
- Redis cache services are used for refresh and synchronization patterns.

## Models and Utility Highlights

This codebase includes reusable model/helper layers that are useful for portfolio demonstration.

- `gui/dataclass/base.py`
	- `DataclassBaseModel` extends pydantic behavior.
	- includes recursive `as_dict()` conversion.
	- includes `dumps()` / `loads()` serialization helpers.
	- includes websocket model auto-discovery and model selection from payload.
- `gui/utils/handlers/math/utility_calculator.py`
	- contains documented helper methods (docstrings), for example:
		- precise decimal arithmetic
		- datetime parsing helpers
		- quantity range classification
		- geodesic distance (Haversine)
		- currency conversion and numeric validation helpers
- `gui/utils/logger.py`
	- centralized logging setup with colored console output and file logs.
	- global print override and exception hook integration.

## Python 3.13.3 Setup (Detailed)

This project should be run with **Python 3.13.3**.

### 1. Verify Python 3.13.3

Windows (PowerShell):

```powershell
py -3.13 --version
```

Expected output should include `Python 3.13.3`.

If you have multiple Python versions, always force 3.13 when creating the virtual environment.

### 2. Create Virtual Environment

From repository root:

```powershell
py -3.13 -m venv .venv
```

### 3. Activate Virtual Environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If execution policy blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Command Prompt (`cmd`):

```bat
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 4. Upgrade Packaging Tools

```powershell
python -m pip install --upgrade pip setuptools wheel
```

### 5. Install Dependencies

All dependencies are listed in `requirements.txt`.

```powershell
pip install -r requirements.txt
```

### 6. Confirm Environment

```powershell
python --version
pip --version
```

`python --version` should show `3.13.3` while the venv is active.

## Configuration

The application expects `gui/config/config.py` to exist and contain valid runtime values.

1. Use `gui/config/config_example.py` as your reference.
2. Ensure every required class/attribute exists in `config.py`.
3. Provide local values for:
	 - database credentials
	 - redis settings
	 - websocket settings
	 - launcher/update endpoint settings
	 - file paths and style config

Important:

- Do not commit real secrets/tokens to public repositories.
- Keep private keys and credentials outside versioned source whenever possible.

## Run the Application

From repository root with active venv:

```powershell
python -m gui
```

Or simply:

```powershell
python gui
```

Alternative (direct file execution):

```powershell
python gui\__main__.py
```

## Build (PyInstaller)

Spec file is available at `flugi_app.spec`.

Example:

```powershell
pyinstaller flugi_app.spec
```

Output artifacts will be generated under the standard PyInstaller output folders.

## Development Notes

- The app has explicit handling for Windows-specific async edge cases (for example WinError 995 suppression in runtime patches).
- Startup validates config structure against `config_example.py` to prevent missing fields at runtime.
- Background workers and external integrations are started only after core runtime setup.
- HTML templates in `gui/templates/` support document rendering workflows.

## Troubleshooting

### venv activation does not work in PowerShell

Use temporary policy bypass:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Wrong Python version in venv

Delete and recreate `.venv` explicitly with Python 3.13:

```powershell
Remove-Item -Recurse -Force .venv
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

### Import/module errors at startup

- confirm venv is active
- reinstall dependencies with `pip install -r requirements.txt`
- verify `gui/config/config.py` contains all required fields from `config_example.py`

## Legal Notice

Copyright (c) 2025 FLUGI69.
All rights reserved.

This repository and its source code are protected by copyright law.
Use, modification, redistribution, or public reuse may require explicit permission from the owner.
