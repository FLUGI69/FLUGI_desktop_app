from sshtunnel import SSHTunnelForwarder
import types
from typing import Union
import sys

from ..string import String
from ..file import File

from threading import Lock
import logging

from .reconnect_service import SSHTunnelReconnectService
from utils.logger import LoggerMixin

class SSHTunnel(LoggerMixin):

    reconnect_service: SSHTunnelReconnectService

    log: logging.Logger

    def __init__(self,
        name: str,
        ssh_host: str,
        ssh_port: int = 22,
        ssh_user: str = "ubuntu",
        ssh_pass: Union[str, types.NoneType] = None,
        ssh_private_key_ppk_path: Union[str, types.NoneType] = None,
        sql_hostname: str = "127.0.0.1",
        sql_port: int = 3306,
        ):

        self.name = name

        self.__lock = Lock()

        self.__reconnect_service = None

        if ssh_private_key_ppk_path is not None and ssh_private_key_ppk_path != "":
            
            if File.checkIsExists(ssh_private_key_ppk_path) == True and File.checkIsFile(ssh_private_key_ppk_path):
               
                privkey_exist = True
                
                ssh_pass = None
           
            else:
                
                self.log.warning("%s | Not found Private key ppk: %s" % (str(self.name),str(ssh_private_key_ppk_path)))
                
                sys.exit(0)
        
        else:
            
            privkey_exist = False

        self.log.debug("%s | Remote server SSHTunnel Forwarder: Host: %s, Port: %s, User: %s, Passwd: %s, Privkey: %s," % (
            str(self.name),
            str(ssh_host),
            str(ssh_port),
            str(ssh_user),
            str(String.maskString(ssh_pass, 1) if privkey_exist == False else None),
            str(privkey_exist)
        ))

        self.tunnel = SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username = ssh_user,
            ssh_password = ssh_pass,
            ssh_pkey = ssh_private_key_ppk_path,
            remote_bind_address = (sql_hostname, sql_port)
        )
        
        self.thread = None

    def start(self):

        self.log.info("%s | Remote server SSHTunnel -> Connect" % (str(self.name)))

        self.tunnel.start()

    def stop(self):
        
        self.log.info("%s | Remote server SSHTunnel -> Stop" % (str(self.name)))

        self.reconnect_service.is_running = False 

        try:
            
            if self.tunnel.is_active:
                
                self.tunnel.stop()

            if self.reconnect_service.reconnect_thread:
                
                self.reconnect_service.reconnect_thread.join(timeout = 2)

        except Exception as e:
            
            self.log.warning("%s | Failed to stop SSHTunnel: %s" % (str(self.name), str(e)))
    
    @property
    def local_bind_port(self):

        return self.tunnel.local_bind_port
    
    @property
    def reconnect_service(self):
        
        with self.__lock:
            
            return self.__reconnect_service

    @reconnect_service.setter
    def reconnect_service(self, value):
        
        if isinstance(value, SSHTunnelReconnectService):
            
            with self.__lock:
                
                self.__reconnect_service = value