from typing import Callable

from threading import Thread, Lock
from time import sleep
import logging
from time import sleep

from threading import Lock
import typing as t

from .connections import SSHTunnelConnections, SSHTunnelConnection
from utils.logger import LoggerMixin

if t.TYPE_CHECKING:
    
    from .sshtunnel import SSHTunnel

class SSHTunnelReconnectService(LoggerMixin):
    
    log: logging.Logger

    def __init__(self,
        tunnel: 'SSHTunnel',
        ):
      
        self.ssh_tunnel = tunnel
        
        self.ssh_tunnel.reconnect_service = self
    
        self.__reconnect_callback = None
        
        self.__local_bind_port: int = None

        self.reconnect_thread: Thread = None

        self.log.debug("%s | Remote SSHTunnelReconnectService -> Start" % str(self.ssh_tunnel.name))

        self.__is_running: bool = True
        
        self.__lock = Lock()

    @property
    def local_bind_port(self):
        
        with self.__lock:
            
            return self.__local_bind_port

    @local_bind_port.setter
    def local_bind_port(self, value: int):
        
        if isinstance(value, int):
            
            with self.__lock:
                
                self.__local_bind_port = value

    @property
    def is_running(self):
        
        with self.__lock:
            
            return self.__is_running

    @is_running.setter
    def is_running(self, value: bool):
        
        if isinstance(value, bool):
            
            with self.__lock:
                
                self.__is_running = value

    def setReconnectCallback(self, reconnect_callback: Callable):

        self.__reconnect_callback = reconnect_callback

    def start(self):

        while True:

            try:

                self.ssh_tunnel.start()

                self.log.info("%s | Remote SSHTunnel -> Connected" % (str(self.ssh_tunnel.name)))

                self.local_bind_port = self.ssh_tunnel.local_bind_port

                self.__start_reconnect_thread()

                # RedisConnection.setDB(self.name, db)

                break

            except Exception as err:

                self.log.warning("%s | Remote SSHTunnel -> Connection retry... (%s)" % (str(self.ssh_tunnel.name), str(err)))

                sleep(3)

    def __start_reconnect_thread(self):
            
            self.log.debug("%s | Remote SSHTunnel -> Start reconnect thread" % (str(self.ssh_tunnel.name)))
            
            self.reconnect_thread = Thread(
                name = "SSHTunnelReconnectThread-%s" % (str(self.ssh_tunnel.name)), 
                target = self.__start_reconnect,
                daemon = True
            )

            self.reconnect_thread.start()

    def __start_reconnect(self):
        
        while True:
            
            if self.ssh_tunnel.tunnel.is_active:
                
                sleep(1)
                
            else:

                if self.is_running:
                    
                    self.ssh_tunnel.stop()
                    
                break

        if not self.is_running:
            
            self.log.debug("%s | Remote SSHTunnel -> Skipping reconnect, shutdown in progress" % str(self.ssh_tunnel.name))
            return

        self.log.debug("%s | Remote SSHTunnel -> Reconnect" % str(self.ssh_tunnel.name))
        
        self.start()

        self.log.debug("%s | Remote SSHTunnel -> Trigger callback" % str(self.ssh_tunnel.name))
       
        if self.__reconnect_callback:
            
            self.__reconnect_callback(port = self.local_bind_port)