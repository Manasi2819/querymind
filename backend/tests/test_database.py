import pytest
import os
from sqlalchemy import create_engine
from core.db_init import _get_db_name_from_url, _get_server_url, initialize_database
from database import _build_engine, get_db

def test_get_db_name_from_url():
    url = "mysql+pymysql://root:admin@localhost:3306/queryminddb"
    assert _get_db_name_from_url(url) == "queryminddb"

def test_get_server_url():
    url = "mysql+pymysql://root:admin@localhost:3306/queryminddb"
    server_url = _get_server_url(url)
    assert server_url == "mysql+pymysql://root:admin@localhost:3306"
    
def test_build_engine_sqlite():
    engine = _build_engine("sqlite:///./test.db")
    assert engine.name == "sqlite"
    
def test_build_engine_mysql():
    engine = _build_engine("mysql+pymysql://root:admin@localhost:3306/testdb")
    assert engine.name == "mysql"
    assert engine.pool._timeout == 30 # default
    assert engine.pool._recycle == 3600

def test_initialize_database_sqlite(caplog):
    import logging
    caplog.set_level(logging.INFO)
    # SQLite does not need initialization
    initialize_database("sqlite:///./test.db")
    assert "SQLite detected. No database creation needed." in caplog.text

def test_get_db():
    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass
