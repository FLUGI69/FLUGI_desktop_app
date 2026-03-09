from pathlib import Path
import os, sys
from datetime import datetime, timezone

class Config(object):
    
    class websocket:
        
        is_enabled = False
        host = "0.0.0.0"
        port = 0000
        namespace = "/axample"
        auth_token = ""
        excluded_models = {"", ""}
        folder = "gui/utils/dc/websocket"
        
        class ssh:
        
            host = ""
            port = 0000
            user = ""
            passwd = None
            privateKeyPath = ""
            # privateKeyPath
            
    class mutex:
        
        name = ""
    
    class dev:
    
        class db:
        
            user = ""
            password = ""
            host = "127.0.0.1"
            port = 1234
            database = ""
        
        class redis:
                
            host = "127.0.0.1"
            port = 1234
            db = 0
            password = ""

    class styleSheets:
        """Note: In PyQt, QSS stylesheets can only be reliably applied to widgets that 
        are not deeply nested or highly recursive in the widget hierarchy.
        This limitation is why I also define separate style configurations in the config 
        class, in addition to QSS, to ensure consistent styling."""
        
        success = """
            background-color: #5cb85c;
            color: white;
            border-radius: 8px;
            padding: 4px 8px;
        """
        failed = """
            background-color: #d72329;
            color: white;
            border-radius: 8px;
            padding: 4px 8px;
        """
        warning = """
            background-color: #FFD700;
            color: white;
            border-radius: 8px;
            padding: 4px 8px;
        """
        work_scroll = """ 
            background-color: transparent;
            border: none;
        """
        work_text_edit = """
            border-radius: 8px;
            border: none;
            padding-left: 8px;
            background: qradialgradient(
                cx:0.5, cy:0.5,
                fx:0.5, fy:0.5, 
                radius:1, 
                stop:0 #6e6e6e, 
                stop:1 #3e3e3e
            );
            color: white;
            font-size: 16px;
        """
        work_btn = """
            QPushButton#WorkBtn {
                background-color: #5a5a5a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#WorkBtn:hover {
                background-color: #7a7a7a;
            }
            QPushButton#WorkBtn:pressed {
                background-color: #9a9a9a;
            }
        """
        work_storage_items = """
            QPushButton#SelectFormItem {
                background-color: #5a5a5a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold; 
            }
            QPushButton#SelectFormItem:hover {
                background-color: #7a7a7a;
            }
            QPushButton#SelectFormItem:pressed {
                background-color: #9a9a9a;
            }
        """
        work_form_list = """
            QListWidget#FormItemList {
                border: 1px solid;
                border-radius: 8px;
                border-color: #0a0a0a;
            }
        """
        work_add_components_search = """
            QLineEdit#WorkSearch {
                border-radius: 8px;
                padding-left: 8px;
                background: qradialgradient(
                    cx:0.5, cy:0.5,
                    fx:0.5, fy:0.5, 
                    radius:1, 
                    stop:0 #6e6e6e, 
                    stop:1 #3e3e3e
                );
                color: white;
                height: 50px;
                font-size: 16px;
            }
        """
        dropdown_style = """
            QComboBox#Dropdown {
                background: qradialgradient(
                    cx: 0.5, cy: 0.5,
                    fx: 0.5, fy: 0.5,
                    radius: 1,
                    stop: 0 #6e6e6e,
                    stop: 1 #3e3e3e
                );
                border: none;
                border-radius: 8px;
                padding: 4px 32px 4px 8px; 
                color: #ffffff;       
                font-size: 14px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right; 
                width: 24px;                  
                border: none;
                margin: 2px;
                border-radius: 8px;            
                background-color: transparent; 
            }
            QComboBox::drop-down:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QComboBox::down-arrow {
                image: url("gui/config/icons/arrow-down.svg");
                width: 20px;
                height: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #4e4949;
                border: none;
                color: white;
                selection-background-color: rgba(66, 133, 244, 0.35);
                selection-color: white;
                outline: 0;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(66, 133, 244, 0.20);
            }
            QComboBox QAbstractItemView {
                background-color: #3e3e3e;
                border: 1px solid #5a5a5a;
                color: white;
                selection-background-color: rgba(66, 133, 244, 0.35);
                selection-color: white;
                border-radius: 6px;
                padding: 4px;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 8px;
                border: none;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(66, 133, 244, 0.2);
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: rgba(66, 133, 244, 0.35);
            }
        """
        date_time_select = """
            QDateTimeEdit#Date {
                background: qradialgradient(
                    cx: 0.5, cy: 0.5,
                    fx: 0.5, fy: 0.5,
                    radius: 1,
                    stop: 0 #6e6e6e,
                    stop: 1 #3e3e3e
                );
                border: none;
                border-radius: 8px;
                padding: 4px 32px 4px 8px; 
                color: #ffffff;       
                font-size: 14px;
            }
            QDateTimeEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right; 
                width: 24px;                  
                border: none;
                margin: 2px;
                border-radius: 8px;            
                background-color: transparent; 
            }
            QDateTimeEdit::drop-down:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QDateTimeEdit::down-arrow {
                image: url("gui/config/icons/arrow-down.svg");
                width: 20px;
                height: 20px;
            }
            QCalendarWidget {
                background-color: #3e3e3e;
                border: 1px solid #5a5a5a;
                color: white;
                border-radius: 8px;
            }
            QCalendarWidget QToolButton {
                background-color: #5a5a5a;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #7a7a7a;
            }
            QCalendarWidget QMenu {
                background-color: #4e4949;
                color: white;
                border: 1px solid #5a5a5a;
            }
            QCalendarWidget QSpinBox {
                background-color: #5a5a5a;
                color: white;
                border: none;
            }
            QCalendarWidget QSpinBox::up-button,
            QCalendarWidget QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 16px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #4e4949;
                border-bottom: 1px solid #5a5a5a;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #3e3e3e;
                color: white;
                selection-background-color: rgba(66, 133, 244, 0.35);
                selection-color: white;
                gridline-color: #5a5a5a;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #4e4949;
                border-bottom: 1px solid #5a5a5a;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #3e3e3e;
                color: white;
                selection-background-color: rgba(66, 133, 244, 0.35);
                selection-color: white;
                gridline-color: #5a5a5a;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """
        label = """
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """
        scroll_area = """
            QScrollArea#ScrollModal {
                background-color: #5a5a5a;
            }
        """
        line_edit = """
            QLineEdit {
                border-radius: 8px;
                padding-left: 8px;
                background: qradialgradient(
                    cx:0.5, cy:0.5,
                    fx:0.5, fy:0.5, 
                    radius:1, 
                    stop:0 #6e6e6e, 
                    stop:1 #3e3e3e
                );
                color: white;
                height: 50px;
                font-size: 16px;
            }
        """
        text_edit = """
            QTextEdit {
                border-radius: 8px;
                padding: 4px;
                background: qradialgradient(
                    cx:0.5, cy:0.5,
                    fx:0.5, fy:0.5,
                    radius:1,
                    stop:0 #6e6e6e,
                    stop:1 #3e3e3e
                );
                color: white;
                font-size: 14px;
            }
        """
        table_widget = """
            QTableWidget {
                background-color: #6e6e6e;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                gridline-color: #5a5a5a;
                margin-top: 10px;
            }
        """
        
    class html_setup:
        
        class admin_storage_content:
            
            header = """
            <div style='font-size:12pt; text-align:left; margin-bottom:10px;'>
                Example Company Ltd.<br>
                1234 City Example street 11.<br>
                Example City, Country<br>
            </div>
            """
            title = "<h2 style='text-align:center; margin-bottom: 5px;'>MACHINES AND EQUIPMENT INVENTORY</h2>"
           
    class launcher:
        
        remote_version = "https://api.github.com/repos/name/app_name/contents/version.json?ref=main"
        remote_update_zip = "https://raw.githubusercontent.com/name/app_name/main/app.zip"
        access_token = "hash_git_token"
        accept_json = "application/vnd.github.v3+json"
        accept_stream = "application/octet-stream"
    
    class log:
        
        level = "DEBUG"                    
        file_name = "app.log" 
        path = r""                 
        fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        print_level = 15
        
        class filehandler:
            
            maxBytes = 5*1024*1024 
            backupCount = 3       
            encoding = "utf-8"
            
    class qr_code:
        
        path = r""                 

    class style:
        
        path = "gui/static/assets/css/style.qss"    
        
    class openapi:
        
        key = "openapi_key"    
        
    class icon:

        @staticmethod
        def base_path():
            
            if getattr(sys, 'frozen', False):
                
                return os.path.join(os.path.dirname(sys.executable), "_internal/gui/config")
            
            return os.path.dirname(os.path.abspath(__file__))

        icon_dir = os.path.join(base_path(), "icons")
        
    class flags:
        
        @staticmethod
        def base_path():
            
            if getattr(sys, 'frozen', False):
                
                return os.path.join(os.path.dirname(sys.executable), "_internal/gui")
            
            return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        flag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "assets", "img", "flags")  
            
    class time:

        # The DB stores business timestamps in local time, so use local tz consistently.
        timezone_local = datetime.now().astimezone().tzinfo or timezone.utc
        # Backward-compatible alias used across the project.
        timezone_utc = timezone_local
        timeformat = "%Y-%m-%d %H:%M:%S"
        
    class ip_info:
        
        url = "https://ipinfo.io/json"
        
    class google:
        
        api_name = "gmail"
        api_version = "v1"
        user_id = "me"
        uri = "https://gmail.googleapis.com/"
        scopes = ["https://mail.google.com/"]
        batch_size = 15
        batch_uri = "https://gmail.googleapis.com/batch/gmail/v1"
        page_size = 30
        
        class paths:
            
            logo = "gui/static/assets/img/cts_logo.png"
            google_icon = "gui/static/assets/img/google_logo.png"
            
        class credentials:
            
            secret = {
                "installed": {
                    "client_id":"",
                    "project_id":"",
                    "auth_uri":"",
                    "token_uri":"",
                    "auth_provider_x509_cert_url":"",
                    "client_secret":"",
                    "redirect_uris":[""]
                }
            }
            
    class img:
        
        main_window_bg_path = ""
        
    class gif:
        
        #relative path
        confused_path = ""
        spinner = ""
        empty_mailbox = ""
        donald_money = ""
        
    class db:
        
        user = ""
        password = ""
        host = ""
        port = ""
        database = ""
        
        class ssh:
            
            host = ""
            port = 1234
            user = ""
            passwd = None
            privateKeyPath = "C:\\.ppk"
            # privateKeyPath
        
    class redis:
        
        host = ""
        port = ""
        db = 0
        password = ""
        
        class ssh:
            
            host = ""
            port = 1234
            user = ""
            passwd = None
            privateKeyPath = "C:\\.ppk"
            # privateKeyPath
        
        class cache:
            
            class material:
                
                id = datetime.now().strftime("%y-%m")
                exp = 3600
                
            class marine_traffic:
                
                exp = 3600
                
            class admin_boat_info:
                
                id = datetime.now().strftime("%y-%m")
                exp = 3600
                
                class single_boat:
                        
                    exp = 600
                        
            class reminders:
                
                exp = 3600
                        
            class tools:
                
                id = datetime.now().strftime("%y-%m")
                exp = 3600
               
            class devices:
                
                id = datetime.now().strftime("%y-%m")
                exp = 3600
                
            class returnable_packaging:
                
                id = datetime.now().strftime("%y-%m")
                exp = 3600
            
            class storage:
                
                target = "dropdown"
                id = datetime.now().strftime("%y-%m")
                exp = 3600
                
            class storage_items:
                
                target = "table"
                id = datetime.now().strftime("%y-%m")
                exp = 3600
                
            class tenants:
                
                id = datetime.now().strftime("%y-%m")
                exp = 3600
                
            class rental_history:
                
                exp = 3600
                
    class web_scraper:
        
        sock_connect = 10
        
        sock_read = 60
        
        class mahart_ports:
            
            url = "https://www.example.hu/"
            
    class marine_traffic:
        
        playwright_dir = r""
        base_url = "example.com"
        target_uri = "example.com/ships"
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) OPR/108.0.0.0 Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/120.0.6099.234 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) CriOS/122.0.6261.100 Mobile/15E148 Safari/537.36",
        ]
        langs = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.8",
            "de-DE,de;q=0.9,en;q=0.8",
            "fr-FR,fr;q=0.9,en;q=0.8",
            "es-ES,es;q=0.9,en;q=0.8",
            "nl-NL,nl;q=0.9,en;q=0.8",
            "hu-HU,hu;q=0.9,en;q=0.8",
            "pl-PL,pl;q=0.9,en;q=0.8",
            "it-IT,it;q=0.9,en;q=0.8",
            "sv-SE,sv;q=0.9,en;q=0.8",
        ] 
        viewports = [(1366,768), (1440,900), (1536,864), (1920,1080)]   
               
        class overpass:
            
            url = "https://overpass.kumi.systems/api/interpreter"
            delta = 0.5    
