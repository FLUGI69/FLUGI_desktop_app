import sys
from pathlib import Path
import logging
import re

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from async_loop.qt_app import QtApplication
from launcher import Launcher
from utils.logger import LoggerMixin
from config.config import Config

class Interfaces(LoggerMixin):
    
    log: logging.Logger

    @classmethod
    async def __run_launcher(cls, qt_app: QtApplication):
        
        launcher = Launcher(qt_app)
        
        await launcher.run()
            
    @staticmethod
    async def __after_shutdown(qt_app: QtApplication):
        
        if hasattr(qt_app, "redis_client"):
            
            await qt_app.redis_client.close()

    @staticmethod
    async def __after_startup(qt_app: QtApplication) -> None:
            
        qt_app.log.info("Application UI ready")

    @classmethod
    async def __setup_database(cls, qt_app: QtApplication) -> None:
        
        await qt_app.add_background_task(qt_app.db.connect_database(
            user = Config.db.user if qt_app.is_dev_mode == False else Config.dev.db.user,
            password = Config.db.password if qt_app.is_dev_mode == False else Config.dev.db.password,
            host = Config.db.host if qt_app.is_dev_mode == False else Config.dev.db.host,
            port = Config.db.port if qt_app.is_dev_mode == False else Config.dev.db.port,
            db_name = Config.db.database if qt_app.is_dev_mode == False else Config.dev.db.database,
            sshtunnel_host = Config.db.ssh.host if qt_app.is_dev_mode == False else None,
            sshtunnel_port = Config.db.ssh.port if qt_app.is_dev_mode == False else None,
            sshtunnel_user = Config.db.ssh.user if qt_app.is_dev_mode == False else None,
            sshtunnel_pass = Config.db.ssh.passwd if qt_app.is_dev_mode == False else None,
            sshtunnel_private_key_path = Config.db.ssh.privateKeyPath if qt_app.is_dev_mode == False else None, 
            db_size_check = True
        ))

    @classmethod
    async def __setup_redis(cls, qt_app: QtApplication):
        
        await qt_app.add_background_task(qt_app.redis_client.setup_redis(
            host = Config.redis.host if qt_app.is_dev_mode == False else Config.dev.redis.host,
            port = Config.redis.port if qt_app.is_dev_mode == False else Config.dev.redis.port,
            db = Config.redis.db if qt_app.is_dev_mode == False else Config.dev.redis.db,
            password = Config.redis.password if qt_app.is_dev_mode == False else Config.dev.redis.password,
            sshtunnel_host = Config.redis.ssh.host if qt_app.is_dev_mode == False else None,
            sshtunnel_port = Config.redis.ssh.port if qt_app.is_dev_mode == False else None,
            sshtunnel_user = Config.redis.ssh.user if qt_app.is_dev_mode == False else None,
            sshtunnel_pass = Config.redis.ssh.passwd if qt_app.is_dev_mode == False else None,
            sshtunnel_private_key_path = Config.redis.ssh.privateKeyPath if qt_app.is_dev_mode == False else None
        ))
        
        qt_app.log.info("AsyncRedisClient initialized")

    @classmethod
    def setup_app(cls, info, app: QApplication):
        
        cls.log.info(cls._format_info(info))
        
        qt_app = QtApplication(app)
        
        style_path = Config.style.path

        if getattr(sys, "frozen", False):
            
            base_path = Path(sys.executable).parent / "_internal"
       
            style_path = base_path / style_path
        
        else: 
            
            base_path = Path(__file__).parent.parent.parent

        with open(style_path, "r", encoding = "utf-8") as f:
            
            style = f.read()
        
        style = re.sub(r'url\(["\']?([^"\')]+)["\']?\)', lambda match: cls.fix_url(
            match = match, 
            base_path = base_path
        ), style)

        qt_app.app.setStyleSheet(style)
        
        icon_path = base_path / "gui/static/assets/img/svg/cts_logo.svg"
        
        qt_app.app.setWindowIcon(QIcon(str(icon_path)))
            
        return qt_app 
    
    @classmethod
    def fix_url(cls, match, base_path):
        
        rel_path = match.group(1)
        abs_path = (base_path / rel_path).resolve()
        
        return f'url("{abs_path.as_posix()}")'

    @classmethod
    def _format_info(cls, info: dict) -> str:
        
        width = 80 
        
        lines = []

        lines.append("")
        lines.append("=" * width)
        lines.append(cls._center("FLUGI - application information", width))
        lines.append("-" * width)

        for key, value in info.items():
            
            k = key.replace("_", " ").capitalize()
            
            line = f"{k}: {value}"
            
            lines.append(cls._center(line, width))

        lines.append("=" * width)
        
        return "\n".join(lines)

    @staticmethod
    def _center(text: str, width: int) -> str:
        
        return text.center(width)

    @classmethod
    def run(cls, qt_app: QtApplication):
        
        qt_app.register_before_startup(cls.__run_launcher)
        
        qt_app.register_before_startup(cls.__setup_database)
        
        qt_app.register_before_startup(cls.__setup_redis)
        
        qt_app.register_after_startup(cls.__after_startup)
        
        qt_app.register_before_shutdown(cls.__after_shutdown)
        
        qt_app.run()
