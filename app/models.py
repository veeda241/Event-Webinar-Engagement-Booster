from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    job_title = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    interests = Column(String, nullable=True)
    preferred_contact_method = Column(String, default="email")
    phone_number = Column(String, nullable=True)

    registrations = relationship("Registration", back_populates="user")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    event_time = Column(DateTime)
    recording_url = Column(String, nullable=True)

    registrations = relationship("Registration", back_populates="event")

class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    registration_time = Column(DateTime)
    job_id = Column(String, nullable=True) # Store the main job ID for this registration

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")