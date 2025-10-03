from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# Base schemas for reuse
class UserBase(BaseModel):
    email: EmailStr
    name: str
    job_title: Optional[str] = None
    phone_number: Optional[str] = None
    preferred_contact_method: Optional[str] = 'email'
    interests: Optional[str] = None

class EventBase(BaseModel):
    name: str
    description: str
    event_time: datetime

# Schema for user output (never expose password)
class User(UserBase):
    id: int
    is_admin: bool
    class Config:
        from_attributes = True

# Schema for returning an event, including its ID
class Event(EventBase):
    id: int

    class Config:
        from_attributes = True

# Schema for creating a new user via registration
class UserCreate(UserBase):
    password: str


# Schema for creating a new event
class EventCreate(EventBase):
    pass

# Schema for a new registration request from an authenticated user
class EventRegistrationRequest(BaseModel):
    event_id: int

class RegistrationResponse(BaseModel):
    message: str
    user_email: EmailStr
    event_id: int

# Schema for chatbot requests
class ChatRequest(BaseModel):
    query: str

# Schema for user login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schemas for JWT Tokens
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None