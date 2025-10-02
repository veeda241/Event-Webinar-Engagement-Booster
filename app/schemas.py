from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Base schemas for reuse
class UserBase(BaseModel):
    email: EmailStr
    name: str
    interests: Optional[str] = None

class EventBase(BaseModel):
    name: str
    description: str
    event_time: datetime

# Schema for creating a new user via registration
class UserCreate(UserBase):
    pass

# Schema for creating a new event
class EventCreate(EventBase):
    pass

# Schema for a new registration
class RegistrationCreate(BaseModel):
    user: UserCreate
    event_id: int

class RegistrationResponse(BaseModel):
    message: str
    user_email: EmailStr
    event_id: int