import asyncio
import logging
import typing as t
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from utils.logger import LoggerMixin
from .api_view import GmailApiView
from utils.handlers.installed_app_flow import FlugiAppFlow
from utils.dc.user_device import UserDevice
from utils.dc.google_token import GoogleToken
from db import queries
from config import Config

class UserClientView(GmailApiView, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        user_id: str, 
        scopes: list[str],
        user_device: UserDevice
        ):
        
        self.is_authorized = False
    
        self.user_id = user_id
        
        self.scopes = scopes
        
        self.user_device = user_device
        
        self.creds: t.Optional[Credentials] = None
        
    async def check_google_token_exists(self):
        
        existed_token = await queries.select_google_token_exists(self.user_device.guid)
        
        self.log.info("Checking existing token for user device: %s", self.user_device.guid)
        
        if existed_token is not None:
            # print(existed_token.__dir__())

            token_info = GoogleToken(
                token = existed_token.token,
                refresh_token = existed_token.refresh_token,
                token_uri = existed_token.token_uri,
                client_id = existed_token.client_id,
                client_secret = existed_token.client_secret, 
                scopes = [scope.name for scope in existed_token.scopes],
                expiry = existed_token.expiry.isoformat() if existed_token.expiry is not None else None,
                universe_domain = existed_token.universe_domain
            )

            self.log.debug("Existing token found: %s", token_info)
            
            try:
                
                self.creds = Credentials.from_authorized_user_info(
                    info = token_info.as_dict(), 
                    scopes = self.scopes
                )
        
                self.is_authorized = self.creds.valid
                
            except Exception as e:
                
                self.log.warning("Failed to load saved token, will request new OAuth flow | Reason: %s" % str(e))
        
    async def authorize(self) -> Credentials:
        
        try:
            
            if self.creds is not None:
                # print(self.creds.__dir__())

                if self.creds.valid is True:
                    
                    self.log.info("Using existing valid credentials")
                    
                    self.is_authorized = True
                    
                    return self.creds
                
                elif self.creds.expired is True and self.creds.refresh_token:
                    
                    self.log.info("Refreshing expired credentials")
                    
                    await asyncio.get_running_loop().run_in_executor(None, self.creds.refresh, Request())
                    
                    await queries.update_google_token_by_guid(
                        guid = self.user_device.guid,
                        token = self.creds.token,
                        expiry = self.creds.expiry if self.creds.expiry is not None else None
                    )
                    
                    self.is_authorized = self.creds.valid
                    
                    return self.creds

            else:
                
                self.log.info("No existing credentials, starting OAuth flow")
                
                # flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.scopes)
                flow = FlugiAppFlow.from_client_config(
                    client_config = Config.google.credentials.secret, 
                    scopes = self.scopes
                )
                
                self.creds = await asyncio.get_running_loop().run_in_executor(None, lambda: flow.run_local_server(port = 0))
              
                """ 
                credentials = google.oauth2.credentials.Credentials(
                    session.token["access_token"],
                    refresh_token=session.token.get("refresh_token"),
                    id_token=session.token.get("id_token"),
                    token_uri=client_config.get("token_uri"),
                    client_id=client_config.get("client_id"),
                    client_secret=client_config.get("client_secret"),
                    scopes=session.scope,
                    granted_scopes=session.token.get("scope"),
                )
                """

                await queries.insert_user_device_token_login_info(
                    guid = self.user_device.guid,
                    device_name = self.user_device.device_name,
                    os = self.user_device.os,
                    ip_address = self.user_device.ip_address,
                    location = self.user_device.location,
                    success = True if self.creds.valid else False,
                    token = self.creds.token,
                    refresh_token = self.creds.refresh_token,
                    token_uri = self.creds.token_uri,
                    client_id = self.creds.client_id,
                    client_secret = self.creds.client_secret,
                    expiry = self.creds.expiry,
                    universe_domain = self.creds.universe_domain,
                    scopes = self.creds.granted_scopes,
                    is_active = True,
                    username = self.user_device.username,
                )
                
                self.is_authorized = self.creds.valid
                
                return self.creds
            
        except asyncio.CancelledError:
            
            self.log.info("OAuth login cancelled by user")
            
            flow.close_local_server()
            
            self.is_authorized = False
            
            return None  
              
        except Exception as e:
            
            self.log.exception("Failed to authorize Gmail credentials: %s" % str(e))
            
            self.is_authorized = False
            
            raise
