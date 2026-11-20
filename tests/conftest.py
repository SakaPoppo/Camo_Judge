"""PostgreSQL integration-test fixtures."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL or TEST_DATABASE_URL is required for PostgreSQL tests")

    source_url = make_url(database_url)
    test_database_name = f"camo_judge_test_{uuid4().hex}"
    admin_url = source_url.set(database="postgres")
    test_url = source_url.set(database=test_database_name)
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{test_database_name}"'))

    try:
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        config.set_main_option(
            "sqlalchemy.url",
            test_url.render_as_string(hide_password=False).replace("%", "%%"),
        )
        command.upgrade(config, "head")
        yield test_url.render_as_string(hide_password=False)
    finally:
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": test_database_name},
            )
            connection.execute(text(f'DROP DATABASE "{test_database_name}"'))
        admin_engine.dispose()


@pytest.fixture(scope="session")
def engine(migrated_database_url: str):
    database_engine = create_engine(migrated_database_url)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as database_session:
        yield database_session
        database_session.rollback()

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE image_files, images, background_types, "
                "camouflage_patterns RESTART IDENTITY CASCADE"
            )
        )
