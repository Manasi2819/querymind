from models.schemas import DBConfig

# Test MySQL URL
c1 = DBConfig(url="mysql+pymysql://user:pass@localhost:3306/db")
print(f"URL: {c1.url} -> db_type: {c1.db_type}")

# Test PostgreSQL URL
c2 = DBConfig(url="postgresql://user:pass@localhost:5432/db")
print(f"URL: {c2.url} -> db_type: {c2.db_type}")

# Test SQLite URL
c3 = DBConfig(url="sqlite:///test.db")
print(f"URL: {c3.url} -> db_type: {c3.db_type}")

# Test case insensitivity
c4 = DBConfig(url="POSTGRESQL://user:pass@localhost:5432/db")
print(f"URL: {c4.url} -> db_type: {c4.db_type}")

# Test default when no URL
c5 = DBConfig(database="test", db_type="postgresql")
print(f"Fields -> db_type: {c5.db_type}")
