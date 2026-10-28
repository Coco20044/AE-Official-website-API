import asyncio
import ssl
from logging.config import fileConfig
from app.models.payment import Payment
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config
from app.models.enrollment import Enrollment
from app.core.config import settings
from app.database.base import Base
from app.models.user import User
from app.models.course import Course
from app.models.cohort import Cohort
from app.models.course_class import CourseClass
from app.models.learning_resource import LearningResource
from app.models.recording import Recording
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.announcement import Announcement
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


database_url = make_url(settings.DATABASE_URL)

database_url = database_url.set(
    drivername="postgresql+asyncpg",
    query={
        key: value
        for key, value in database_url.query.items()
        if key not in {"sslmode", "channel_binding"}
    },
)


def run_migrations_offline() -> None:
    context.configure(
        url=database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    configuration["sqlalchemy.url"] = database_url.render_as_string(
        hide_password=False
    )

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "ssl": ssl.create_default_context(),
        },
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
