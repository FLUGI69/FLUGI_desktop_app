from sqlalchemy import insert, select, update
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from config import Config

class insert_user_device_token_login_info(AsyncQueryBase):
    
    async def query(self,
        guid: str,
        device_name: str, 
        os: str,
        ip_address: str,
        location: str,
        success: bool,             
        token: str, 
        refresh_token: str, 
        token_uri: str, 
        client_id: str, 
        client_secret: str,
        expiry: datetime, 
        universe_domain: str,
        scopes: list[str],
        is_active: bool,
        username: str | None = None,
        ) -> None:

        now = datetime.now()
        
        async with self.session.begin():
            
            user_device_id = await self._insert_user_device(
                username = username,
                guid = guid,
                device_name = device_name,
                os = os,
                ip_address = ip_address,
                location = location,
                created_at = now
            )
            
            if user_device_id is not None:
                
                login_history_id = await self._insert_login_history(
                    user_device_id = user_device_id,
                    login_time = now,
                    success = success
                )

                scope_ids = await self._insert_scope_if_not_exists(scopes)
                
                token_id = await self._insert_user_token(
                    user_device_id = user_device_id,
                    login_history_id = login_history_id,
                    token = token,
                    refresh_token = refresh_token,
                    token_uri = token_uri,
                    client_id = client_id,
                    client_secret = client_secret,
                    expiry = expiry,
                    universe_domain = universe_domain,
                    is_active = is_active
                )
                
                if scope_ids is not None and len(scope_ids) > 0:
                    
                    await self.session.execute(
                        insert(example_db.token_scope),
                        [{"token_id": token_id, "scope_id": socpe_id} for socpe_id in scope_ids]
                    )
    
    async def _insert_user_device(self, 
        guid: str,
        device_name: str,
        os: str,
        ip_address: str,
        location: str,
        created_at: datetime,
        username: str | None = None
        ) -> int:
        
        existing_device_id = await self._select_device_id_by_guid(guid)
        
        if existing_device_id is None:

            result = await self.session.execute(
                insert(
                    
                    example_db.user_device
                    
                ).values(
                    
                    username = username,
                    guid = guid,
                    device_name = device_name,
                    os = os,
                    ip_address = ip_address,
                    location = location,
                    created_at = created_at
                )
            )
            
            user_device_id = result.lastrowid

            if user_device_id is not None:
                
                return user_device_id
            
        else:

            existed_device = await self._select_existed_device_by_id(existing_device_id)
            
            if existed_device is not None:
                
                update_values = {}

                if existed_device.device_name != device_name:
                    
                    update_values["device_name"] = device_name

                if existed_device.os != os:
                    
                    update_values["os"] = os

                if existed_device.ip_address != ip_address:
                    
                    update_values["ip_address"] = ip_address

                if existed_device.location != location:
                    
                    update_values["location"] = location

                if len(update_values) > 0:
                    
                    await self.session.execute(
                        update(
                            
                            example_db.user_device
                            
                        ).where(
                            
                            example_db.user_device.id == existing_device_id
                            
                        ).values(**update_values)
                    )
            
                return existing_device_id

    async def _select_existed_device_by_id(self,
        id: int
        ) -> example_db.user_device | None:
        
        query_result = await self.session.execute(
            select(
                
                example_db.user_device
                
            ).where(
                
                example_db.user_device.id == id
            )
        )
        
        existing_device = query_result.scalar_one_or_none()
        
        return existing_device
    
    async def _select_device_id_by_guid(self, guid: str) -> int | None:
        
        query_result = await self.session.execute(
            select(
                
                example_db.user_device.id
                
            ).where(
                
                example_db.user_device.guid == guid
            )
        )
        
        device_id: int | None = query_result.scalar_one_or_none()
        
        return device_id
    
    async def _insert_login_history(self,
        user_device_id: int,
        login_time: datetime,
        success: bool
        ) -> int:
        
        result = await self.session.execute(
            insert(
                
                example_db.login_history
                
            ).values(
                
                user_device_id = user_device_id,
                login_time = login_time,
                success = success
            )
        )
        
        login_history_id: int = result.lastrowid
        
        if login_history_id is None:
            
            raise ValueError("Failed to insert login history, no ID returned")
        
        return login_history_id
    
    async def _insert_user_token(self,
        user_device_id: int,
        login_history_id: int,
        token: str,
        refresh_token: str,
        token_uri: str,
        client_id: str,
        client_secret: str,
        expiry: datetime,
        universe_domain: str,
        is_active: bool
        ) -> int:
        
        result = await self.session.execute(
            insert(
                
                example_db.google_token
                
            ).values(
                
                user_device_id = user_device_id,
                login_history_id = login_history_id,
                token = token,
                refresh_token = refresh_token,
                token_uri = token_uri,
                client_id = client_id,
                client_secret = client_secret,
                expiry = expiry,
                universe_domain = universe_domain,
                is_active = is_active
            )
        )
        
        token_id: int = result.lastrowid
        
        if token_id is None:
            
            raise ValueError("Failed to insert user token, no ID returned")
        
        return token_id
    
    async def _insert_scope_if_not_exists(self, scopes: list[str]) -> list[int]:
        
        if len(scopes) == 0:
            
            return []

        existing_scopes_result = await self.session.execute(
            select(
                
                example_db.scope
                
            ).where(
                
                example_db.scope.name.in_(scopes)
            )
        )
        
        existing_scopes = existing_scopes_result.scalars().all()
        
        scope_map = {scope.name: Scope(scope.id, scope.name) for scope in existing_scopes}

        new_scopes = [scope for scope in scopes if scope not in scope_map]
        
        if new_scopes is not None and len(new_scopes) > 0:
            
            try:
      
                await self.session.execute(
                    insert(
                        
                        example_db.scope
                        
                    ).values(
                        
                        [{"name": name} for name in new_scopes]
                    )
                )
                
                result = await self.session.execute(
                    select(
                        
                        example_db.scope.id,
                        example_db.scope.name
                        
                    ).where(
                        
                        example_db.scope.name.in_(new_scopes)
                    )
                )
                
                for scope_id, scope_name in result.fetchall():
                    
                    scope_map[scope_name] = Scope(scope_id, scope_name)

            except IntegrityError:
      
                await self.session.rollback()
                
                final_result = await self.session.execute(
                    select(
                        
                        example_db.scope
                        
                    ).where(
                        
                        example_db.scope.name.in_(new_scopes)
                    )
                )
                
                for scope in final_result.scalars():
                    
                    scope_map[scope.name] = Scope(scope.id, scope.name)
        
        return [scope.id for scope in scope_map.values()]

class Scope:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name