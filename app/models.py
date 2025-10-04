from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    hashed_password = Column(String(255))
    job_title = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    interests = Column(String(1024), nullable=True)
    preferred_contact_method = Column(String(50), default="email")
    phone_number = Column(String(50), nullable=True)

    registrations = relationship("Registration", back_populates="user")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(2048))
    event_time = Column(DateTime)
    image_url = Column(String(1024), nullable=True)
    recording_url = Column(String(1024), nullable=True)

    registrations = relationship("Registration", back_populates="event")

class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    registration_time = Column(DateTime)
    job_id = Column(String(255), nullable=True) # Store the main job ID for this registration

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")

from datetime import datetime

class DetailedRegistration(Base):
    __tablename__ = "detailed_registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String(255))
    email = Column(String(255))
    phone_number = Column(String(50), nullable=True)
    payment_info = Column(String(255), nullable=True) # Placeholder for payment details
    consent_agreed = Column(Boolean, default=False)
    team_details = Column(String(1024), nullable=True)
    registration_time = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event")
    user = relationship("User")
