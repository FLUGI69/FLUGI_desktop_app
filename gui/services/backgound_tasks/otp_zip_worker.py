import uuid
import sys
import re
import base64
import zipfile
import subprocess
import urllib.request
import typing as t

try:
    import pyzipper
except ImportError:
    pyzipper = None

from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import logging
import socket
import os
import time

from config import Config
from db.async_redis.async_redis import AsyncRedisClient
from utils.logger import LoggerMixin
from utils.dc.gmail_response_data import MessagePart
from routes.api.google import EmailMessagesView, EmailMessageView
from db import queries

if t.TYPE_CHECKING:
    from routes.api.google import UserClientView

class OTPZipWorker(QObject, LoggerMixin):
    
    log: logging.Logger
    
    finished = pyqtSignal()

    def __init__(self,
        user_client: 'UserClientView',
        redis_client: AsyncRedisClient,
        interval_ms: int = 60000
        ) -> None:
        
        super().__init__()
        
        self.user_client = user_client
        
        self.redis_client = redis_client
        
        self._task: asyncio.Task | None = None
        
        self.interval = interval_ms / 1000
        
        self._target_run_time: datetime | None = None
        
        self._wake_event = asyncio.Event()
        
        self.__running = True
        
        self.__execution_locked = False
        
        self._lock_token: str | None = None

    @property
    def _running(self) -> bool:
        return self.__running is True
    
    @_running.setter
    def _running(self, value: bool):
        self.__running = value
    
    @property
    def _execution_locked(self) -> bool:
        return self.__execution_locked is True
    
    @_execution_locked.setter
    def _execution_locked(self, value: bool):
        self.__execution_locked = value
    
    def stop(self):
        
        self._running = False
        
        self._wake_event.set()
        
        if self._task and self._task.done() == False:
            
            self._task.cancel()

    async def _setup_execution_state(self) -> tuple[datetime, bool]:
          
        scheduled_at, did_insert_schedule = await queries.upsert_next_otp_schedule()

        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo = Config.time.timezone_utc)

        return scheduled_at, did_insert_schedule

    async def _run_after_schedule_insert(self) -> None:

        if self.user_client is None or self.user_client.creds is None:
            
            self.log.warning("No authenticated user client, skipping OTP ZIP download")
            
            return

        start_date, end_date, folder_name = self._previous_month_range()
        
        query = self._build_otp_query(start_date, end_date)

        self.log.debug("Searching OTP ZIP emails with query: %s" % query)

        messages_view = EmailMessagesView(
            user_id = self.user_client.user_id, 
            creds = self.user_client.creds
        )
        
        message_view = EmailMessageView(
            user_id = self.user_client.user_id, 
            creds = self.user_client.creds
        )

        listed = await messages_view.list_user_messages(
            q = query, 
            labelIds = None, 
            pageToken = None, 
            maxResults = None
        )

        if listed.messages is None or len(listed.messages) == 0:
            
            self.log.info("No OTP ZIP emails found for period %s" % folder_name)
            
            return
        
        self.log.info("Found %d OTP email(s) for period %s" % (len(listed.messages), folder_name))

        base_dir = self._resolve_otp_zip_base_dir()
        
        target_dir = base_dir / folder_name
        
        target_dir.mkdir(parents = True, exist_ok = True)

        if any(target_dir.iterdir()):
            
            self.log.warning("Target directory '%s' is not empty, skipping OTP ZIP download" % target_dir)
            
            return

        saved_count = 0

        for msg_stub in listed.messages:
            
            try:
                
                full_msg = await message_view.get_message_by_id(id = msg_stub.id)
                
            except Exception as e:
                
                self.log.error("Failed to fetch message %s: %s" % (msg_stub.id, str(e)))
                
                continue

            if full_msg.payload is None:
                
                self.log.warning("Message %s has no payload skipping" % msg_stub.id)
                
                continue

            sender = self._extract_sender_from_payload(full_msg.payload)
            
            if self._is_otp_sender(sender) == False:
                
                self.log.debug("Message %s sender '%s' is not OTP skipping" % (msg_stub.id, sender))
                
                continue

            zip_parts = self._collect_zip_parts(full_msg.payload)
            
            if len(zip_parts) == 0:
                
                self.log.debug("Message %s has no ZIP attachments" % msg_stub.id)
                
                continue

            for filename, data_b64, attachment_id in zip_parts:
                
                try:
                    
                    if attachment_id is not None:
                        
                        self.log.info("Downloading large attachment '%s' via attachmentId" % filename)
                        
                        data_b64 = await message_view.get_attachment_data(
                            message_id = msg_stub.id, 
                            attachment_id = attachment_id
                        )
                        
                        if data_b64 is None:
                            
                            self.log.error("Failed to download attachment '%s' from message %s" % (filename, msg_stub.id))
                            
                            continue
                    
                    raw_bytes = self._decode_base64url(data_b64)
                    
                    safe_name = self._safe_filename(filename)
                    
                    file_path = target_dir / safe_name
                    
                    await asyncio.to_thread(file_path.write_bytes, raw_bytes)
                    
                    saved_count += 1
                    
                    self.log.debug("Saved OTP ZIP: %s (%d bytes)" % (file_path, len(raw_bytes)))
                    
                    await asyncio.to_thread(
                        self._extract_zip_with_password,
                        file_path, 
                        target_dir / file_path.stem
                    )
                    
                    await asyncio.to_thread(file_path.unlink)
                    
                    self.log.debug("Deleted ZIP after extraction: %s" % file_path)
                    
                except Exception as e:
                    
                    self.log.error("Failed to save attachment '%s' from message %s: %s" % (
                        filename, 
                        msg_stub.id, 
                        str(e)
                    ))

        self.log.info("OTP ZIP download complete: %d file(s) saved to %s" % (saved_count, target_dir))

        await asyncio.to_thread(self._print_pdfs, target_dir)

    def _previous_month_range(self) -> tuple[datetime, datetime, str]:
        
        now = datetime.now(Config.time.timezone_utc)
        
        first_of_current = now.replace(day = 1, hour = 0, minute = 0, second = 0, microsecond = 0)
        
        last_of_prev = first_of_current - timedelta(days = 1)
        
        first_of_prev = last_of_prev.replace(day = 1)
        
        folder_name = "%s_%s" % (
            first_of_prev.strftime("%Y-%m-%d"),
            last_of_prev.strftime("%Y-%m-%d")
        )

        return first_of_prev, last_of_prev, folder_name

    def _build_otp_query(self, start_date: datetime, end_date: datetime) -> str:
        
        after = start_date.strftime("%Y/%m/%d")
        
        before = (end_date + timedelta(days = 1)).strftime("%Y/%m/%d")

        return "from:noreply@otpbank.hu has:attachment filename:zip after:%s before:%s" % (after, before)

    def _resolve_otp_zip_base_dir(self) -> Path:
        
        if getattr(sys, "frozen", False):
            
            return Path(sys.executable).parent / "otp_zip_worker"
        
        return Path(Config.otp_zip_worker.path)

    def _extract_sender_from_payload(self, payload: MessagePart) -> str | None:
        
        if payload is None or payload.headers is None:
            
            return None
        
        for header in payload.headers:
            
            if isinstance(header.name, str) and header.name.lower() == "from":
                
                return header.value
        
        return None

    def _is_otp_sender(self, sender: str | None) -> bool:
        
        if sender is None:
            
            return False
        
        return "noreply@otpbank.hu" in sender.lower()

    def _collect_zip_parts(self, part: MessagePart) -> list[tuple[str, str, str | None]]:
        
        results: list[tuple[str, str, str | None]] = []
        
        if part is None:
            return results

        if (part.filename is not None and isinstance(part.filename, str) 
            and part.filename.lower().endswith(".zip")):
            
            if part.body is not None and isinstance(part.body.data, str) and part.body.data != "":
                results.append((part.filename, part.body.data, None))
                
            elif part.body is not None and isinstance(part.body.attachmentId, str) and part.body.attachmentId != "":
                results.append((part.filename, "", part.body.attachmentId))

        if part.parts is not None and isinstance(part.parts, list):
            
            for subpart in part.parts:
                
                results.extend(self._collect_zip_parts(subpart))

        return results

    def _get_sumatra_dir(self) -> Path:
        
        return Path(Config.sumatra_pdf.base_path())

    def _get_sumatra_path(self) -> Path:
        
        return self._get_sumatra_dir() / Config.sumatra_pdf.exe_name

    def _ensure_sumatra_pdf(self) -> Path | None:
        
        sumatra_path = self._get_sumatra_path()
        
        if sumatra_path.exists() == True:
            
            self.log.debug("SumatraPDF already exists: %s" % sumatra_path)
            
            return sumatra_path
        
        sumatra_dir = self._get_sumatra_dir()
        
        sumatra_dir.mkdir(parents = True, exist_ok = True)
        
        zip_path = sumatra_dir / "SumatraPDF.zip"
        
        self.log.debug("Downloading SumatraPDF from %s" % Config.sumatra_pdf.url)
        
        try:
            
            req = urllib.request.Request(
                Config.sumatra_pdf.url,
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                }
            )
            
            with urllib.request.urlopen(req, timeout = 120) as resp:
                
                zip_path.write_bytes(resp.read())
            
            self.log.debug("Downloaded SumatraPDF to %s" % zip_path)
            
        except Exception as e:
            
            self.log.error("Failed to download SumatraPDF: %s" % str(e))
            
            return None
        
        try:
            
            with zipfile.ZipFile(zip_path, "r") as zf:
                
                zf.extractall(path = sumatra_dir)
            
            zip_path.unlink()
            
            self.log.debug("Extracted SumatraPDF to %s" % sumatra_dir)
            
        except Exception as e:
            
            self.log.error("Failed to extract SumatraPDF: %s" % str(e))
            
            return None
        
        if sumatra_path.exists() == False:
            
            self.log.error("SumatraPDF exe not found after extraction: %s" % sumatra_path)
            
            return None
        
        return sumatra_path

    def _get_physical_printer(self) -> str | None:
        
        try:
            
            result = subprocess.run([
                "powershell",
                "-NoProfile",
                "-Command",
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " +
                "Get-Printer | Where-Object {$_.Name -notmatch 'Fax|XPS|PDF|OneNote'} | Select-Object -First 1 -ExpandProperty Name"],
                capture_output = True,
                text = True,
                encoding = "utf-8",
                timeout = 10
            )
            
            name = result.stdout.strip()
            
            self.log.info("RAW printer repr: %s" % repr(name))

            if name != "":
           
                name = name.replace("\xa0", " ")
                name = name.replace("\r", "").replace("\n", "")
                name = name.strip()

                return name
        
        except Exception as e:
            
            self.log.error("Failed to detect physical printer: %s" % str(e))
        
        return None

    def _print_pdfs(self, target_dir: Path) -> None:
        
        sumatra_path = self._ensure_sumatra_pdf()
        
        if sumatra_path is None:
            
            self.log.error("SumatraPDF is not available, skipping PDF print")
            
            return
        
        printer_name = self._get_physical_printer()
        
        if printer_name is None:
            
            self.log.error("No physical printer found (Fax/XPS/PDF filtered), skipping PDF print")
            
            return
        
        self.log.info("Using printer: '%s'" % printer_name)
        
        subdirs = sorted([d for d in target_dir.iterdir() if d.is_dir()])
        
        if len(subdirs) == 0:
            
            self.log.info("No subdirectories found in %s, nothing to print" % target_dir)
            
            return
        
        for subdir in subdirs:
            
            pdf_files = sorted(subdir.glob("*.pdf"))
            
            if len(pdf_files) == 0:
                
                self.log.debug("No PDF files in %s" % subdir)
                
                continue
            
            for pdf_path in pdf_files:
                
                try:
                    
                    self.log.debug("Printing PDF (SumatraPDF): %s" % pdf_path)
                    
                    subprocess.run(
                        [
                            str(sumatra_path),
                            "-silent",
                            "-print-to", printer_name,
                            str(pdf_path)
                        ],
                        check = True,
                        timeout = 60
                    )
                
                except subprocess.TimeoutExpired:
                    
                    self.log.warning("Print timed out for %s" % pdf_path)
                
                except Exception as e:
                    
                    self.log.error("Failed to print PDF %s: %s" % (pdf_path, str(e)))
                    
            break
        
    def _extract_zip_with_password(self, zip_path: Path, output_dir: Path) -> None:
        
        password = Config.otp_zip_worker.passwrd.encode("utf-8")
        
        output_dir.mkdir(parents = True, exist_ok = True)
        
        try:
            
            with zipfile.ZipFile(zip_path, "r") as zf:
                
                zf.extractall(path = output_dir, pwd = password)
            
            self.log.debug("Extracted ZIP (zipfile): %s -> %s" % (zip_path, output_dir))
            
            return
            
        except RuntimeError as e:
            # self.log.warning("zipfile extract failed for %s: %s" % (zip_path, str(e)))
            pass
        
        except zipfile.BadZipFile as e:
            
            self.log.error("Invalid ZIP file %s: %s" % (zip_path, str(e)))
            
            return
        
        except Exception as e:
            
            self.log.exception("Zipfile unexpected error for %s: %s" % (zip_path, str(e)))
        
        if pyzipper is None:
            
            self.log.error("pyzipper is not installed, cannot fallback-extract %s" % zip_path)
            
            return
        
        try:
            
            with pyzipper.AESZipFile(zip_path, "r") as zf:
                
                zf.pwd = password
                
                zf.extractall(path = output_dir)
            
            self.log.debug("Extracted ZIP (pyzipper fallback): %s -> %s" % (zip_path, output_dir))
        
        except Exception as e:
            
            self.log.exception("AESZipFile fallback failed for %s: %s" % (zip_path, str(e)))

    @staticmethod
    def _decode_base64url(data: str) -> bytes:
        
        padded = data + "=" * ((4 - len(data) % 4) % 4)
        
        return base64.urlsafe_b64decode(padded)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        
        safe = re.sub(r'[<>:"/\\|?*]', "_", filename)
        
        safe = safe.strip(". ")
        
        if safe == "":
            
            safe = "attachment.zip"
        
        return safe

    def _lock_key(self) -> str:
        return "lock:otp_execution"
    
    def _make_lock_token(self) -> str:
        return "%s:%s:%s" % (socket.gethostname(), os.getpid(), uuid.uuid4().hex)

    async def _is_execution_locked(self) -> bool:
        
        current = await self.redis_client.client.get(self._lock_key())
        
        if current is None:
            return False
        
        return True

    async def _try_acquire_execution_lock(self) -> bool:
        
        token = self._make_lock_token()
        
        acquired = await self.redis_client.client.set(
            self._lock_key(),
            token,
            ex = 1800,
            nx = True
        )
        
        if acquired is True:
            self._lock_token = token
            return True
        
        return False

    async def _release_execution_lock(self) -> None:
        
        result = await self.redis_client.client.eval(
            Config.redis.cache.lock_release_script,
            1,
            self._lock_key(),
            self._lock_token
        )
        
        released = result == 1
        
        if released == True:
            
            self.log.info("Released OTP execution lock (lock key: '%s' released=%s) -> Lock end" % (
                self._lock_key(),
                str(released)
            ))
            
        else:
            
            self.log.warning("OTP execution lock was not owned by this client (lock key: '%s' released=%s) -> Lock end" % (
                self._lock_key(),
                str(released)
            ))
        
        self._lock_token = None
        
        self._execution_locked = False

    async def _wait_for_lock_or_acquire(self) -> bool:
        
        waited = False
        last_log = time.monotonic()
        
        while self._running == True:
            
            acquired = await self._try_acquire_execution_lock()
            
            if acquired == True:
                
                self._execution_locked = True
                
                if waited == True:
                    
                    self.log.info("Acquired OTP execution lock (lock key: '%s') after wait -> Lock begin" % self._lock_key())
                    
                else:
                    
                    self.log.info("Acquired OTP execution lock (lock key: '%s') -> Lock begin" % self._lock_key())
                
                return True
            
            now = time.monotonic()
            
            if waited == False or now - last_log >= 5:
                
                current_holder = await self.redis_client.client.get(self._lock_key())
                
                self.log.debug("Waiting for OTP execution lock (lock key: '%s') to be released, held by %s -> Lock wait" % (
                    self._lock_key(),
                    current_holder.decode("utf-8") if isinstance(current_holder, bytes) else str(current_holder)
                ))
                
                last_log = now
                waited = True
            
            self._wake_event.clear()
            
            try:
                
                await asyncio.wait_for(self._wake_event.wait(), timeout = 5)
                
            except asyncio.TimeoutError:
                pass
        
        return False

    async def _run_loop(self):
        
        self._task = asyncio.current_task()
        
        self.log.info("OTPZipWorker -> Start")
        
        try:
            
            while self._running == True:
                
                acquired = await self._wait_for_lock_or_acquire()
                
                if acquired == False:
                    
                    self.log.info("OTP zip worker stopped while waiting for lock")
                    
                    break
                
                try:

                    self._target_run_time, did_insert_schedule = await self._setup_execution_state()

                    if did_insert_schedule == True:

                        await self._run_after_schedule_insert()

                except Exception as e:
                    
                    self.log.exception("Exception during OTP execution lock (lock key: '%s'): %s" % (
                        self._lock_key(),
                        str(e)
                    ))
                    raise
                    
                finally:
                    
                    await self._release_execution_lock()
                    
                    subprocess.run([
                        "taskkill", "/F", "/IM", "SumatraPDF.exe"
                    ], capture_output = True)
                    
                    subprocess.run([
                        "taskkill", "/F", "/IM", "SumatraPDF-3.6.1-64.exe"
                    ], capture_output = True)
                
                self.log.debug("OTP zip worker scheduled for %s" % self._target_run_time.isoformat())
                
                while self._running == True:
                    
                    now = datetime.now(Config.time.timezone_utc)
                    delta = (self._target_run_time - now).total_seconds()
                    
                    if delta <= 0:
                        break
                    
                    sleep_seconds = max(1, min(delta, self.interval))
                    
                    self._wake_event.clear()
                    
                    try:
                        
                        await asyncio.wait_for(self._wake_event.wait(), timeout = sleep_seconds)
                        
                    except asyncio.TimeoutError:
                        pass

        except asyncio.CancelledError:
            raise
        
        finally:
            
            self.finished.emit()
    
