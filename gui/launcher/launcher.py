import asyncio
import json
import os
import requests
import subprocess
import zipfile
import time
import sys
from pathlib import Path
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
import base64
import logging
import mimetypes
import shutil
import tempfile

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
        
        self.app_zip_path = self.root_path.parent / "example_app.zip"
        
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

    def download_update(self, remote_version: str):
        
        release_url = f"{self.remote_update_zip_url}/v{remote_version}"
        
        self.log.info("Fetching release info from %s" % release_url)

        api_headers = {
            "Authorization": f"Bearer {Config.launcher.access_token}",
            "Accept": Config.launcher.accept_json
        }

        meta_response = requests.get(
            url = release_url,
            headers = api_headers,
            timeout = 15
        )
        
        meta_response.raise_for_status()
        
        release_data = meta_response.json()
        
        assets = release_data.get("assets", [])
        
        asset = None
        
        for a in assets:
            
            if a["name"] == "example_app.zip":
                
                asset = a
                
                break
        
        if not asset:
            
            raise RuntimeError("Release asset 'example_app.zip' not found in latest release")
        
        asset_url = asset["url"]
        
        asset_size = asset.get("size", 0)
        
        self.log.info("Downloading asset from %s (%d bytes)" % (asset_url, asset_size))
        
        download_headers = {
            "Authorization": f"Bearer {Config.launcher.access_token}",
            "Accept": "application/octet-stream"
        }

        response = requests.get(
            url = asset_url,
            headers = download_headers,
            stream = True,
            timeout = 120
        )

        self.log.debug("Response status: %s" % response.status_code)
            
        response.raise_for_status()
        
        total_length = asset_size or int(response.headers.get('content-length', 0))

        downloaded = 0
        chunk_size = 8192

        with open(self.app_zip_path, "wb") as f:
            
            for chunk in response.iter_content(chunk_size = chunk_size):
                
                if chunk:
                    
                    f.write(chunk)
                    
                    downloaded += len(chunk)
                    
                    if total_length > 0:
                    
                        progress = int(downloaded * 100 / total_length)
                    
                        self.set_progress_value_safe(progress)

        self.set_progress_value_safe(100)
        
        self.log.info("Download finished (%d bytes)" % downloaded)
        
    def apply_update(self):
        
        if not zipfile.is_zipfile(self.app_zip_path):
            
            mime_type, _ = mimetypes.guess_type(str(self.app_zip_path))
            
            self.log.error("Update file is not a valid ZIP. File: %s (detected type: %s)" % (
                self.app_zip_path.name,
                mime_type or "unknown"
                )
            )
            
            raise RuntimeError("Downloaded file is not a valid ZIP")

        install_dir = Path(sys.executable).parent
        
        temp_base = Path(tempfile.gettempdir()) / "example_app_update"
        
        if temp_base.exists():
            
            shutil.rmtree(temp_base)
        
        self.log.info("Extracting update to %s" % temp_base)
        
        with zipfile.ZipFile(self.app_zip_path, "r") as zip_ref:
            
            zip_ref.extractall(temp_base)
        
        source_dir = temp_base / "example_app"
        
        if not source_dir.exists() or not (source_dir / "example_app.exe").exists():
            
            self.log.error("Invalid update package structure. Expected example_app/ with example_app.exe inside")
            
            shutil.rmtree(temp_base)
            
            raise RuntimeError("Invalid update package structure")
        
        self.log.info("Update extracted. source_dir: %s, install_dir: %s" % (source_dir, install_dir))
        
        updater_bat = Path(tempfile.gettempdir()) / "example_app_updater.bat"
        
        pid = os.getpid()
        
        script = (
            '@echo off\n'
            'chcp 65001 >nul\n'
            ':waitloop\n'
            'ping 127.0.0.1 -n 2 >nul\n'
            f'del /F /Q "{install_dir}\\example_app.exe" >nul 2>&1\n'
            f'if exist "{install_dir}\\example_app.exe" goto waitloop\n'
            f'robocopy "{source_dir}\\_internal" "{install_dir}\\_internal" /MIR /NFL /NDL /NJH /NJS /R:3 /W:2 >nul 2>&1\n'
            f'copy /Y "{source_dir}\\example_app.exe" "{install_dir}\\" >nul 2>&1\n'
            f'rmdir /S /Q "{temp_base}" >nul 2>&1\n'
            f'del /F /Q "{self.app_zip_path}" >nul 2>&1\n'
            f'start "" "{install_dir}\\example_app.exe"\n'
            '(goto) 2>nul & del "%~f0"\n'
        )
        
        updater_bat.write_text(script, encoding = "utf-8")
        
        self.log.info("Launching updater script (PID: %d)" % pid)
        
        subprocess.Popen(
            ['cmd', '/c', str(updater_bat)],
            creationflags = subprocess.CREATE_NO_WINDOW,
            close_fds = True
        )
        
        self.log.info("Updater script launched, application will exit for update")

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
                
                self.set_label_text_safe("Verzió ellenőrzése...")
                
                await asyncio.sleep(0.1)
                
                local_version = await asyncio.to_thread(self.get_local_version)
                
                remote_data = await asyncio.to_thread(self.get_remote_version_data)
                
                remote_version = remote_data["version"]

                self.log.info("Local version: %s, Remote version: %s" % (local_version, remote_version))
                
                self.set_label_text_safe(f"Helyi verzió: {local_version}\nTávoli verzió: {remote_version}")
                
                await asyncio.sleep(1)

                if self.is_update_needed(local_version, remote_version):
                    
                    self.set_label_text_safe("Frissítés szükséges, letöltés...")
                    
                    await asyncio.sleep(0.1)
                    
                    await asyncio.to_thread(self.download_update, remote_version)
                    
                    self.set_label_text_safe("Frissítés telepítése...")
                    
                    await asyncio.sleep(0.1)
                    
                    await asyncio.to_thread(self.apply_update)
                    
                    self.set_label_text_safe("Újraindítás...")
                    
                    await asyncio.sleep(1)
                    
                    self.window.hide()
                    
                    sys.exit(0)
                    
                else:
                    
                    self.set_progress_value_safe(100)
                    
                    self.set_label_text_safe("Nincs frissítés. Alkalmazás indítása...")

                await asyncio.sleep(1)
                
                self.window.hide()

        except Exception as e:
            
            self.log.exception("Launcher error: %s" % (str(e),))
            
            sys.exit(1)
                 
    def set_label_text_safe(self, text: str):
        
        if self.window and hasattr(self.window, 'label'):
            
            QMetaObject.invokeMethod(
                self.window.label,
                "setText",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, text)
            )

    def set_progress_value_safe(self, value: int):
        
        if self.window and hasattr(self.window, 'progress'):
            
            QMetaObject.invokeMethod(
                self.window.progress,
                "setValue",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, value)
            )