import argparse
from pathlib import Path


def init_db(args: argparse.Namespace) -> None:
    """
    Initialize Alembic for the project.
    """
    base_path = Path.cwd()
    migrations_dir = base_path / "migrations"
    alembic_ini_path = base_path / "alembic.ini"

    if migrations_dir.exists():
        print("Migrations directory already exists.")
        return

    print(f"Initializing migrations in {migrations_dir}...")
    migrations_dir.mkdir(parents=True)
    (migrations_dir / "versions").mkdir()

    # Create alembic.ini
    with open(alembic_ini_path, "w") as f:
        f.write(
            f"""[alembic]
script_location = migrations
sqlalchemy.url = sqlite+aiosqlite:///./test.db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
        )

    # Create env.py
    # We need a template that works with Async logic
    env_py_content = """import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ------------------------------------------------------------------------
# PLEASE UPDATE THIS IMPORT TO POINT TO YOUR ACTUAL SQLALCHEMY BASE
# from myapp.database import Base
# target_metadata = Base.metadata
# ------------------------------------------------------------------------
target_metadata = None

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
"""

    with open(migrations_dir / "env.py", "w") as f:
        f.write(env_py_content)

    # Create script.py.mako
    script_mako_content = """<%!
import re

def slugify(text):
    text = str(text).strip().lower()
    return re.sub(r'[-\\s]+', '_', text)

%>\
\"\"\"${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

\"\"\"
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
"""
    with open(migrations_dir / "script.py.mako", "w") as f:
        f.write(script_mako_content)

    print("Done. Please edit 'migrations/env.py' to import your 'Base' metadata.")


def main() -> None:
    parser = argparse.ArgumentParser(description="RealFastAPI CLI")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init-db", help="Initialize Alembic migrations")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
