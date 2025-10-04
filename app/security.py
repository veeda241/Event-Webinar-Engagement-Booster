import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os

from . import schemas

# Define the path to the users.json file
USERS_FILE = Path(__file__).parent.parent / "users.json"

# Password Hashing
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_in_env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # bcrypt has a 72-byte limit. We check the byte length here.
    if len(password.encode('utf-8')) > 72:
        # Truncate the original string password and pass it to the hasher.
        # Passlib will handle the final encoding.
        return pwd_context.hash(password[:72])
    return pwd_context.hash(password)

def _read_users():
    if not USERS_FILE.exists():
        return []
    with open(USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _write_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(email: str, password: str):
    users = _read_users()
    user_data = next((u for u in users if u["email"] == email), None)
    
    if not user_data:
        return False
    if not verify_password(password, user_data["hashed_password"]):
        return False
    return schemas.User(**user_data)

def create_user(user: schemas.UserCreate):
    users = _read_users()
    
    if any(u["email"] == user.email for u in users):
        raise HTTPException(status_code=400, detail="Email already registered")

    is_first_user = not users
    
    hashed_password = get_password_hash(user.password)
    
    new_user_id = users[-1]["id"] + 1 if users else 1

    new_user_data = {
        "id": new_user_id,
        "email": user.email,
        "name": user.name,
        "hashed_password": hashed_password,
        "job_title": user.job_title,
        "is_admin": is_first_user,
        "interests": user.interests,
        "preferred_contact_method": user.preferred_contact_method,
        "phone_number": user.phone_number,
        "profile_image_url": None,
    }
    
    users.append(new_user_data)
    _write_users(users)

    if is_first_user:
        print(f"First user created ({user.email}) and has been granted admin privileges.")
    
    return schemas.User(**new_user_data)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users = _read_users()
    user_data = next((u for u in users if u["email"] == email), None)

    if user_data is None:
        raise credentials_exception
    return schemas.User(**user_data)

def get_current_admin_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have administrative privileges"
        )
    return current_user

def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    
    users = _read_users()
    user_data = next((u for u in users if u["email"] == email), None)

    if user_data is None:
        return None
    return schemas.User(**user_data)

def update_user_profile(email: str, user_update: schemas.UserUpdate):
    users = _read_users()
    user_found = False
    for i, user in enumerate(users):
        if user["email"] == email:
            users[i]["name"] = user_update.name
            users[i]["job_title"] = user_update.job_title
            users[i]["interests"] = user_update.interests
            users[i]["profile_image_url"] = user_update.profile_image_url
            user_found = True
            break
    if not user_found:
        return None
    _write_users(users)
    return schemas.User(**users[i])

def update_user_contact(email: str, contact_update: schemas.ContactUpdate):
    users = _read_users()
    user_found = False
    for i, user in enumerate(users):
        if user["email"] == email:
            users[i]["preferred_contact_method"] = contact_update.preferred_contact_method
            users[i]["phone_number"] = contact_update.phone_number
            user_found = True
            break
    if not user_found:
        return None
    _write_users(users)
    return schemas.User(**users[i])
