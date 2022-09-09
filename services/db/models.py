from sqlalchemy import MetaData, Column, Integer, String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from os import environ

__all__ = (
    'BaseModel',
)

from sqlalchemy.orm import registry

metadata = MetaData(schema=environ.get('TG_NOTIFICATION_BOT_DB_SCHEMA'))
BaseModel = declarative_base(metadata=metadata)
mapper_registry = registry()


class Chain(BaseModel):
    __tablename__ = 'chain'

    key = Column(String, primary_key=True)
    name = Column(String)
    coin_symbol = Column(String)


class TrackingMap(BaseModel):
    __tablename__ = 'tracking_map'

    id = Column(Integer, primary_key=True)
    chain_key = Column(String, ForeignKey('chain.key'))
    user_id = Column(Integer)
    wallet = Column(String)
    custom_name = Column(String)
    __table_args__ = (UniqueConstraint('chain_key', 'user_id', 'wallet', name='_user_wallet_uc'),
                      UniqueConstraint('user_id', 'custom_name', name='_user_custom_name_uc'))


class TrackingMapLog(BaseModel):
    __tablename__ = 'tracking_map_log'

    id = Column(Integer, primary_key=True)
    chain_key = Column(String, ForeignKey('chain.key'))
    user_id = Column(Integer)
    wallet = Column(String)
    custom_name = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
