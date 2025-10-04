from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    Manages application settings using Pydantic.
    It automatically reads environment variables from a .env file.
    """
    # --- Application Settings ---
    DATABASE_URL: str
    SECRET_KEY: str = "a_very_strong_and_secret_key_for_jwt" # In production, this should be a real secret set in the .env file
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- LLM Configuration ---
    ENABLE_LOCAL_LLM: bool = True
    LLM_MODEL_NAME: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

    # --- Messaging Services ---
    SENDGRID_API_KEY: str = "YOUR_SENDGRID_API_KEY"
    SENDGRID_FROM_EMAIL: str = "your-verified-sender@example.com"
    TWILIO_ACCOUNT_SID: str = "YOUR_TWILIO_ACCOUNT_SID"
    TWILIO_AUTH_TOKEN: str = "YOUR_TWILIO_AUTH_TOKEN"
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886" # e.g., 'whatsapp:+14155238886'

    # This configuration tells Pydantic to load from a .env file
    # and, crucially, to ignore any extra environment variables it finds.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()