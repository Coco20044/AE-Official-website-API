import ssl
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

database_url = make_url(settings.DATABASE_URL)

database_url = database_url.set(drivername="postgresql+asyncpg", query={
    key : value
    for key, value in database_url.query.items()
    if key not in {"sslmode", "channel_binding"}
},)
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    connect_args={
        "ssl":ssl.create_default_context(),
    }
)