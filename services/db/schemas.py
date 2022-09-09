from typing import Optional

from pydantic.main import BaseModel


class ChainSchema(BaseModel):
    key: str
    name: str
    coin_symbol: str

    class Config:
        orm_mode = True


class TrackingMapSchema(BaseModel):
    id: int
    chain_key: str
    user_id: int
    wallet: str
    custom_name: Optional[str]

    class Config:
        orm_mode = True
