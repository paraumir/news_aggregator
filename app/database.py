from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:23052004*xX@localhost/news_db"
DATABASE_URL = "postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>"


engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with async_session() as session:
        await session.execute(text("SET client_encoding = 'UTF8';"))
        yield session
