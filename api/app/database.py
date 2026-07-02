"""Database engine/session setup and one-time bootstrap of the app database.

The shared `pgdb` Postgres instance already hosts other databases (mlflow,
dagster, ...). This service stores its data in a dedicated database
(`keycloak_slurm_map`) so it never touches those. The database is created on
startup if it does not yet exist.
"""
import logging

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_settings = get_settings()
engine = create_engine(_settings.app_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_database_exists() -> None:
    """Create the dedicated application database if it is missing."""
    s = get_settings()
    conn = psycopg2.connect(
        host=s.postgres_host,
        port=s.postgres_port,
        user=s.postgres_user,
        password=s.postgres_password,
        dbname=s.postgres_maintenance_db,
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (s.app_db_name,))
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(s.app_db_name))
                )
                logger.info("Created database %s", s.app_db_name)
            else:
                logger.info("Database %s already exists", s.app_db_name)
    finally:
        conn.close()


def init_db() -> None:
    """Bootstrap database + tables. Safe to call repeatedly."""
    ensure_database_exists()
    # Import models so they are registered on the metadata before create_all.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # create_all() never alters existing tables, so add columns introduced
    # after the table was first created. Idempotent.
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE team_slurm_token "
                "ADD COLUMN IF NOT EXISTS meluxina_project_name VARCHAR(255)"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
