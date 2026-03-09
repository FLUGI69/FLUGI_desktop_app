import asyncio
import json
import requests
import zipfile
import time
import sys
from pathlib import Path
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
import base64
import logging
import mimetypes
import shutil

from view.launcher.launcher_window import LauncherWindow
from config import Config
from utils.logger import LoggerMixin
from async_loop.qt_app import QtApplication
import version 

class Launcher(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, qt_app: QtApplication):
        
        self.qt_app = qt_app
        
        if getattr(sys, "frozen", False):
            
            self.root_path = Path(sys.executable).parent / "_internal"
            
            self.version_path = self.root_path / "gui/version.json"
            
        else: 
            
            self.root_path = Path(__file__).parent.parent.parent
            
            self.version_path = self.root_path / "gui/version.json"

        self.remote_version_url = Config.launcher.remote_version
        
        self.remote_update_zip_url = Config.launcher.remote_update_zip
        
        self.app_zip_path = self.root_path.parent / "App.zip"
        
        self.is_dev_mode = False if getattr(sys, "frozen", False) else True
        
        self.window = None

    def generate_version_json_from_py(self):
        
        ver_str = ".".join(map(str, version.VERSION))
        
        data = {"version": ver_str}
        
        if (not self.version_path.exists()) or (json.loads(self.version_path.read_text())["version"] != ver_str):
            
            self.version_path.write_text(json.dumps(data, indent = 2), encoding = "utf-8")
            
            self.log.info("Generated/updated version.json with version %s" % (ver_str,))

    def get_local_version(self):
        
        if not self.version_path.exists():
            
            if self.is_dev_mode == True:
            
                self.generate_version_json_from_py()
            
            else:
                
                self.log.error("Missing version.json at %s" % self.version_path.resolve())
            
                sys.exit(1)
                
        with open(self.version_path, "r", encoding = "utf-8") as f:
            
            data = json.load(f)
            
        return data.get("version", "0.0.0.0")

    def get_remote_version_data(self):
        
        self.log.info("Fetching remote version data from %s" % (self.remote_version_url,))
        
        headers = {
            "Authorization": f"Bearer {Config.launcher.access_token}",
            "Accept": Config.launcher.accept_json
        }
   
        response = requests.get(
            url = self.remote_version_url, 
            headers = headers, 
            timeout = 10
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        content_b64 = data.get("content")
        
        if not content_b64:
            
            raise RuntimeError("No content in version.json response")
        
        decoded_bytes = base64.b64decode(content_b64)
        
        decoded_str = decoded_bytes.decode("utf-8")
        
        json_data = json.loads(decoded_str)
        
        return json_data

    def is_update_needed(self, local_version, remote_version) -> bool:
        
        return tuple(map(int, remote_version.split("."))) > tuple(map(int, local_version.split(".")))

    def download_update(self):
        
        self.log.info("Downloading update from %s" % (self.remote_update_zip_url))

        headers = {
            "Authorization": f"Bearer {Config.launcher.access_token}",
            "Accept": Config.launcher.accept_stream
        }

        response = requests.get(
            url = self.remote_update_zip_url,
            headers = headers,
            stream = True,
            timeout = 30
        )

        self.log.debug("Response headers: %s" % (response.headers))
            
        response.raise_for_status()
        
        total_length = int(response.headers.get('content-length', 0))
        
        if total_length == 0:
            
            raise RuntimeError("Cannot get content-length for progress bar")

        downloaded = 0
        chunk_size = 8192

        with open(self.app_zip_path, "wb") as f:
            
            for chunk in response.iter_content(chunk_size = chunk_size):
                
                if chunk:
                    
                    f.write(chunk)
                    
                    downloaded += len(chunk)
                    
                    progress = int(downloaded * 100 / total_length)
                    
                    self.set_progress_value_safe(progress)

        self.log.info("Download finished")
        
    # def apply_update(self):
        
    #     if not zipfile.is_zipfile(self.app_zip_path):
            
    #         mime_type, _ = mimetypes.guess_type(self.app_zip_path)
            
    #         self.log.error("Update file is not a valid ZIP. File: %s (detected type: %s)" % (
    #             self.app_zip_path.name,
    #             mime_type or "unknown"
    #             )
    #         )
            
    #         return
        
    #     self.log.info("Applying update from %s" % self.app_zip_path)

    #     with zipfile.ZipFile(self.app_zip_path, "r") as zip_ref:
            
    #         zip_ref.extractall(self.root_path)

    #     self.app_zip_path.unlink()

        

    #     else:
            
    #         self.log.warning("Expected nested structure not found, skipping merge step")

    #     self.log.info("Update applied successfully")

    async def run(self):
        
        self.window = LauncherWindow()
        
        self.window.show()

        try:

            if self.is_dev_mode == True:
                
                self.generate_version_json_from_py()
                
                self.log.info("Development mode detected - skipping update check")
                
                self.window.label.setText("Development mode - initializing...")

                self.window.progress.setValue(0)
                
                for i in range(1, 101):
                    
                    await asyncio.sleep(0.01)
                    
                    self.set_progress_value_safe(i)

                self.window.label.setText("Starting application...")
                
                await asyncio.sleep(0.5)

                self.window.hide()
                
                return 
            
            elif self.is_dev_mode == False:
                
                local_version = await asyncio.to_thread(self.get_local_version)
                
                remote_data = await asyncio.to_thread(self.get_remote_version_data)
                
                remote_version = remote_data["version"]

                self.log.info("Local version: %s, Remote version: %s" % (local_version, remote_version))
                
                self.window.label.setText(f"Local version: {local_version}\nRemote version: {remote_version}")

                if self.is_update_needed(local_version, remote_version):
                    
                    self.window.label.setText("Update needed, downloading...")
                    
                    await asyncio.to_thread(self.download_update)
                    
                    self.window.label.setText("Applying update...")
                    
                    # await asyncio.to_thread(self.apply_update)
                    
                    with open(self.version_path, "w", encoding = "utf-8") as f:
                        
                        json.dump({"version": remote_version}, f)
                        
                    self.window.label.setText("Update applied successfully")
                    
                else:
                    
                    self.set_progress_value_safe(100)
                    
                    self.window.label.setText("No update needed. Starting application")

                await asyncio.sleep(1)
                
                self.window.hide()

        except Exception as e:
            
            self.log.exception("Launcher error: %s" % (str(e),))
            
            sys.exit(1)
                 
    def set_progress_value_safe(self, value: int):
        
        if self.window and hasattr(self.window, 'progress'):
            
            QMetaObject.invokeMethod(
                self.window.progress,
                "setValue",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, value)
            )
            