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
    profile_image_url: Optional[str] = None

class EventBase(BaseModel):
    name: str
    description: str
    event_time: Optional[datetime] = None
    image_url: Optional[str] = None

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

# Schema for the AI event importer
class ImportRequest(BaseModel):
    url: str

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

class DetailedRegistrationBase(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    payment_info: Optional[str] = None
    consent_agreed: bool
    team_details: Optional[str] = None

class DetailedRegistrationCreate(DetailedRegistrationBase):
    event_id: int

class DetailedRegistration(DetailedRegistrationBase):
    id: int
    user_id: int
    event_id: int
    registration_time: datetime

    class Config:
        from_attributes = True

class RegistrationAnalysisDetail(DetailedRegistrationBase):
    id: int
    user_id: int
    event_id: int
    registration_time: datetime
    job_title: Optional[str] = None
    interests: Optional[str] = None
    preferred_contact_method: Optional[str] = 'email'

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: str
    job_title: Optional[str] = None
    interests: Optional[str] = None
    profile_image_url: Optional[str] = None

class ContactUpdate(BaseModel):
    preferred_contact_method: str
    phone_number: Optional[str] = None