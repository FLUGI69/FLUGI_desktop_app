from sqlalchemy.ext.asyncio import AsyncSession as AsyncBaseSession
import typing as t

if t.TYPE_CHECKING:
    
    from ..async_session.async_session_maker import AsyncSessionMaker
    
class AsyncSession(AsyncBaseSession):
    
    def __init__(self, 
        parent: 'AsyncSessionMaker', 
        session_name: str = None, 
        **kwargs
        ):
        
        super().__init__(**kwargs)
        
        self.parent = parent
        
        self.session_name = session_name
        
        self.tables = self.parent.parent.tables

        if self.parent.parent.queryTimer:
            
            self.timerStart = self.parent.parent.Timer.start()

    async def close(self):
        
        if self.parent.parent.queryTimer:
            
            funcName = f"AsyncSession - {self.session_name}" if self.session_name else "AsyncSession"
            
            self.parent.parent.timerLog(funcName, self.timerStart)
    
        await super().close()
