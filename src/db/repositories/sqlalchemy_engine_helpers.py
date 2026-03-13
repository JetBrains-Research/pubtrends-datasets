import sqlalchemy
from sqlalchemy import create_engine, Engine
from sqlalchemy.event import listens_for
from sqlalchemy.ext.asyncio import AsyncEngine


def create_async_engine(sqlite_path: str):
    engine = sqlalchemy.ext.asyncio.create_async_engine(f"sqlite+aiosqlite:///{sqlite_path}",
                                                        connect_args={"timeout": 15})
    set_replace_decode_errors(engine.sync_engine)
    set_sqlite_wal_pragma(engine.sync_engine)
    return engine


def create_sync_engine(sqlite_path: str):
    engine = create_engine(f"sqlite:///{sqlite_path}")
    engine.sync_engine = engine
    set_replace_decode_errors(engine)
    return engine


def set_replace_decode_errors(engine: Engine):
    @listens_for(engine, "connect")
    def set_sqlite_text_factory(dbapi_connection, connection_record):
        dbapi_connection.text_factory = lambda x: x.decode(errors="replace")


def set_sqlite_wal_pragma(engine: Engine):
    @listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
