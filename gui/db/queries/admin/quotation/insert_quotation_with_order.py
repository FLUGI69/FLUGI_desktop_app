from sqlalchemy import select, func

from datetime import date

from db.async_query_base.async_query_base import AsyncQueryBase
from db.tables import example_db
from utils.enums.tax_number_type_enum import TaxNumberTypeEnum

class insert_quotation_with_order(AsyncQueryBase):
    
    async def query(self,
        client_name: str,
        client_address: str,
        client_country: str,
        client_tax_number: str,
        client_tax_number_type: TaxNumberTypeEnum,
        project_description: str,
        other_information: str,
        client_tax_number_raw: str = None
    ) -> str:
        
        async with self.session.begin():
            
            result = await self.session.execute(
                select(
                    
                    example_db.client
                
                ).where(
                    
                    example_db.client.tax_number == client_tax_number
                )
            )
            
            client = result.scalars().first()
            
            if client is None:
                
                client = example_db.client(
                    name = client_name,
                    address = client_address,
                    country = client_country,
                    tax_number = client_tax_number,
                    tax_number_raw = client_tax_number_raw,
                    tax_number_type = client_tax_number_type
                )
                
                self.session.add(client)
                
                await self.session.flush()
            
            new_quotation = example_db.quotation(
                client_id = client.id,
                project_description = project_description,
                other_information = other_information
            )
            
            self.session.add(new_quotation)
            
            await self.session.flush()
            
            year = date.today().strftime("%Y")
            
            count_result = await self.session.execute(
                select(func.count()).select_from(
                    
                    example_db.order_number
                
                ).where(
                    
                    example_db.order_number.order_number.like(f"{year}%")
                )
            )
            
            count = count_result.scalar()
            
            order_num = f"{year}{count + 1:04d}"
            
            new_order = example_db.order_number(
                quotation_id = new_quotation.id,
                order_number = order_num
            )
            
            self.session.add(new_order)
            
            return order_num
