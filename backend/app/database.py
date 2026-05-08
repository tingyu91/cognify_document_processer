from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

# asyncpg requires postgresql+asyncpg:// scheme
_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_url, echo=settings.environment == "development", pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
