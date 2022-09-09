import asyncio
import contextlib
from typing import Type, Any
from os import environ

from sqlalchemy import delete, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema

from services.db.models import metadata, BaseModel, TrackingMap


class DbCrud:
    def __init__(self):
        self.DB_USER = environ.get('TG_NOTIFICATION_BOT_DB_USER')
        self.DB_PASSWORD = environ.get('TG_NOTIFICATION_BOT_DB_PASS')
        self.DB_HOST = environ.get('TG_NOTIFICATION_BOT_DB_HOST')
        self.DB_NAME = environ.get('TG_NOTIFICATION_BOT_DB_NAME')
        self.SQLALCHEMY_DATABASE_URL = (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}/{self.DB_NAME}"
        )
        self.engine = None
        self.session_maker = None

    async def start(self):
        self.engine = create_async_engine(
            self.SQLALCHEMY_DATABASE_URL,
            echo=False
        )
        self.session_maker = sessionmaker(self.engine, class_=AsyncSession)

        async with self.engine.begin() as conn:
            if not await conn.run_sync(self.engine.sync_engine.dialect.has_schema, metadata.schema):
                await conn.execute(CreateSchema(metadata.schema))
            # Для пересоздания базы
            # await conn.run_sync(BaseModel.metadata.drop_all)
            await conn.run_sync(BaseModel.metadata.create_all)

    @contextlib.asynccontextmanager
    async def create(self, model_obj: BaseModel):
        async with self._get_session() as session:
            session.add(model_obj)
            await session.commit()
            yield model_obj

    @contextlib.asynccontextmanager
    async def get(self, model_cls: Type[BaseModel], *filters, **filter_by):
        async with self._get_session() as session:
            result = await session.execute(select(model_cls).filter(*filters).filter_by(**filter_by))
            yield result

    @contextlib.asynccontextmanager
    async def update(self, model_cls: Type[BaseModel], new_values: dict, **filter_by):
        async with self._get_session() as session:
            result = await session.execute(update(model_cls).filter_by(**filter_by).values(new_values))
            yield result

    async def delete(self, model_cls: Type[BaseModel], **filter_by: Any):
        if not filter_by:
            raise ValueError('No filters passed.')
        async with self._get_session() as session:
            await session.execute(delete(model_cls).filter_by(**filter_by))
            await session.commit()

    async def execute_raw(self, raw_sql: str):
        async with self._get_session() as session:
            await session.execute(text(raw_sql))
            await session.commit()

    @contextlib.asynccontextmanager
    async def _get_session(self):
        async with self.session_maker() as session:
            async with session.begin():
                yield session


async def addd():
    a = DbCrud()
    await a.start()
    new_tracking = TrackingMap(user_id=123, wallet='123')
    try:
        async with a.create(new_tracking):
            pass
    except IntegrityError as e:
        a = 123


if __name__ == '__main__':
    asyncio.run(addd())
