from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=True) # Made nullable for now to support old users
    job_title = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    interests = Column(String, nullable=True)  # e.g., "AI,Python,Web-Dev"

    registrations = relationship("Registration", back_populates="user")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    event_time = Column(DateTime, nullable=False)
    recording_url = Column(String, nullable=True)

    registrations = relationship("Registration", back_populates="event", cascade="all, delete-orphan")

class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    registration_time = Column(DateTime)

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")