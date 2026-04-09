import pytest
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, JSON, inspect
from migrate_db import _is_mysql, _is_sqlite, _coerce_row, _build_engine, TABLE_ORDER

def test_is_mysql():
    assert _is_mysql("mysql+pymysql://root:admin@localhost:3306/queryminddb") is True
    assert _is_mysql("sqlite:///test.db") is False

def test_is_sqlite():
    assert _is_sqlite("sqlite:///test.db") is True
    assert _is_sqlite("mysql+pymysql://root:admin@localhost:3306/queryminddb") is False

def test_coerce_row():
    # Setup row with stringified JSON (as SQLite would return)
    sqlite_row = {
        "id": 1,
        "name": "test",
        "data": '{"key": "value"}',
        "list_data": '[1, 2, 3]',
        "bad_json": '"{not valid',
        "normal_string": "hello"
    }

    # If target is SQLite, no coercion should happen
    res1 = _coerce_row(sqlite_row, "sqlite:///source.db", "sqlite:///target.db")
    assert isinstance(res1["data"], str)

    # If target is MySQL, JSON strings should become dicts/lists
    res2 = _coerce_row(sqlite_row, "sqlite:///source.db", "mysql+pymysql://localhost/target")
    assert isinstance(res2["data"], dict)
    assert res2["data"]["key"] == "value"
    assert isinstance(res2["list_data"], list)
    assert len(res2["list_data"]) == 3
    
    # Bad JSON stays as string
    assert isinstance(res2["bad_json"], str)
    assert res2["normal_string"] == "hello"

def test_build_engine():
    e1 = _build_engine("sqlite:///test.db")
    assert e1.name == "sqlite"
    
    e2 = _build_engine("mysql+pymysql://root@localhost/test")
    assert e2.name == "mysql"
    assert getattr(e2.pool, "_recycle", None) == 3600
