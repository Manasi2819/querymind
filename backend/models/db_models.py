from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # One-to-one relationship with settings
    settings = relationship("AdminSettings", back_populates="owner", uselist=False)

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("admin_users.id"), unique=True)
    
    # Store settings as JSON bundles
    db_config = Column(JSON, default={})
    llm_config = Column(JSON, default={})
    api_keys = Column(JSON, default={})
    
    owner = relationship("AdminUser", back_populates="settings")
