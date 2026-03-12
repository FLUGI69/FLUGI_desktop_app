import typing as t

from dataclass import DataclassBaseModel

class QuotationTableData(DataclassBaseModel):
    name: str
    quantity: str
    unit: str
    price: str
    line_total: float

class ClientData(DataclassBaseModel):
    name: str
    address: str
    country: str
    vat: str

class QuotationData(DataclassBaseModel):
    currency_symbol: str
    client: ClientData
    items: t.List[QuotationTableData]
