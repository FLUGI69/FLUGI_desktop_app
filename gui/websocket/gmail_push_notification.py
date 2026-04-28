import typing as t 
import logging
import inspect
import logging
import socketio

from utils.logger import LoggerMixin
from utils.dc.websocket.client import WebsocketClient
from utils.dc.websocket.websocket_response import WebsocketResponse
from utils.dc.websocket.websocket_request import WebsocketRequest
from utils.dc.websocket.websocket_request_response import WebsocketRequestResponse
from utils.dc.websocket.auto_message import AutoMessage
from db.network import SSHTunnelConnections, SSHTunnelConnection
from db.network import SSHTunnelReconnectService
from db.network import SSHTunnel
from db.string import String

if t.TYPE_CHECKING:
    
    from async_loop import QtApplication
    
class QtGmailPushNotification(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        app: 'QtApplication', 
        namespace: str,
        ):
        
        self.app = app
        
        self.host = None
        
        self.port = None
        
        self.uri = None
        
        self.namespace = namespace

        self.auth_token = None
        
        self.client_name = f"{self.__class__.__name__}-{id(self)}"
        
        self.ssh_tunnel = None
        
        self.ssh_tunnel_reconnect_service = None
        
        self.sio = socketio.AsyncClient()
        
        self._class_lookup: dict[str, object] | None = None
        
        self._auto_register_handlers(namespace)
    
    @property
    def is_connected(self) -> bool:
        return self.sio.connected
  
    def _auto_register_handlers(self, namespace: str): 
        
        for name, method in inspect.getmembers(self, predicate = inspect.iscoroutinefunction):
            
            if name.startswith("_") or name == "emit":
                continue
            
            else:
                
                self.sio.on(event = name, handler = method, namespace = namespace)
                       
    async def connect(self):
        
        self.log.debug("Connected to Websocket: %s" % (self.uri + self.namespace))

    async def disconnect(self, reason: str):
        
        self.log.debug("Disconnected from Websocket: %s Reason: %s" % (
            self.uri + self.namespace,
            reason
            )
        )
        
    async def websocket_response_ack(self, data):
        
        if isinstance(data, dict):
            
            request_response = WebsocketRequestResponse.model_validate(data)
                                            
            if request_response is not None:
                
                self.log.debug("Received ACK WebSocket response from server: %s" % str(request_response))
                
                if request_response.success == True:
                    
                    self.log.info("%s was successfully handled by the server" % request_response.event)
                    
                else:
                    
                    self.log.warning("Failed to handle %s: %s" % (
                        request_response.event,
                        request_response.error
                        )
                    )
         
    async def gmail_push_notification(self, data):
        
        if isinstance(data, dict):

            websocket_response = WebsocketResponse.model_validate(data)

            self.log.debug("Received WebSocket response from server: %s" % str(websocket_response))
            
            if websocket_response is not None:
                
                if isinstance(websocket_response.data, AutoMessage):
                    
                    self.log.info("%s" % websocket_response.data.message)
            
    async def setup_websocket_event(self,
        host: str,
        port: str,
        auth_token: str,
        sshtunnel_host: str = None,
        sshtunnel_port: int = None,
        sshtunnel_user: str = None,
        sshtunnel_pass: str = None,
        sshtunnel_private_key_path: str = None
        ):
        
        try:

            if sshtunnel_host is not None and sshtunnel_port is not None:
                
                host = "127.0.0.1"
            
                self.ssh_tunnel = SSHTunnel(
                    name = f"Websocket-{self.client_name}",
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
                
                self.uri = f"ws://{host}:{port}"

                self.log.debug("WebsocketClient with SSH tunnel -> Name: %s, Host: %s, Port: %s, Token: %s" % (
                    self.client_name,
                    host,
                    port,
                    String.maskString(auth_token, perc = 1)
                    )
                )
            
            else: 
                
                self.uri = f"ws://{host}:{port}"
                        
                self.log.debug("WebsocketClient direct -> Name: %s, Host: %s, Port: %s, Token: %s" % (
                    self.client_name,
                    
                    host,
                    port,
                    String.maskString(auth_token, perc = 1)
                    )
                )

            self.port = port
            self.host = host
            self.auth_token = auth_token
        
            if self.uri is not None:
      
                await self.sio.connect(
                    url = self.uri, 
                    auth = WebsocketRequest(
                    success = True if self.sio.connected else False,
                    data = WebsocketClient(
                        name = self.client_name,
                        auth_token = auth_token
                    )).model_dump(), retry = True
                )
                
                await self.sio.wait()
                    
        except Exception as e:
      
            self.log.exception("Connection refused maybe server is not running: %s" % str(e))