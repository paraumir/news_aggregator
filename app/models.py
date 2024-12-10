from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text,nullable=False)
    category = Column(String, nullable=True)
    published_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
