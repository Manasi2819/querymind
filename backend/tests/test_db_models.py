import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models.db_models import AdminUser, AdminSettings, UploadedFile, ChatSession, ChatMessage

@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_admin_user_creation(db_session):
    admin = AdminUser(username="test_admin", password_hash="hashed_pass")
    db_session.add(admin)
    db_session.commit()
    assert admin.id is not None
    assert admin.username == "test_admin"

def test_admin_settings_relationship(db_session):
    admin = db_session.query(AdminUser).filter_by(username="test_admin").first()
    settings = AdminSettings(user_id=admin.id, db_config={"url": "test"}, llm_config={"provider": "ollama"})
    db_session.add(settings)
    db_session.commit()
    
    assert admin.settings.id == settings.id
    assert settings.db_config["url"] == "test"

def test_chat_session_and_messages(db_session):
    admin = db_session.query(AdminUser).filter_by(username="test_admin").first()
    chat_session = ChatSession(id="session_123", user_id=admin.id, title="Test Chat")
    db_session.add(chat_session)
    db_session.commit()
    
    assert chat_session.id == "session_123"
    assert chat_session.owner.username == "test_admin"
    
    message = ChatMessage(session_id=chat_session.id, role="user", content="Hello", source="user")
    db_session.add(message)
    db_session.commit()
    
    assert len(chat_session.messages) == 1
    assert chat_session.messages[0].content == "Hello"

def test_uploaded_file(db_session):
    admin = db_session.query(AdminUser).filter_by(username="test_admin").first()
    upload = UploadedFile(user_id=admin.id, filename="test.pdf", file_type="document")
    db_session.add(upload)
    db_session.commit()
    
    assert upload.id is not None
    assert upload.filename == "test.pdf"
