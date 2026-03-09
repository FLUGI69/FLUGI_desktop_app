from threading import Lock
from dataclasses import dataclass

from threading import Lock
import typing as t

if t.TYPE_CHECKING:
    
    from .sshtunnel import SSHTunnel

@dataclass
class SSHTunnelConnection:
    
    ssh_tunnel: 'SSHTunnel' = None

class SSHTunnelConnections:

    __lock = Lock()

    __connections: list[SSHTunnelConnection] = []

    @classmethod
    def get_connections(cls) -> list[SSHTunnelConnection]:

        with cls.__lock:

            return [conn for conn in cls.__connections if isinstance(conn, (SSHTunnelConnection))]
        
    @classmethod
    def add_connection(cls, conn: SSHTunnelConnection):
        
        if isinstance(conn, SSHTunnelConnection):
            
            conn.ssh_tunnel.log.debug("Add '%s' connection to SSHTunnel connections" % (str(conn.ssh_tunnel.name)))
            
            with cls.__lock:
                
                cls.__connections.append(conn)
