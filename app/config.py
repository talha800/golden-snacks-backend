import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Core Metadata Mapping
    PROJECT_NAME: str = Field(default="Mutam Dost Engine Backend")
    ENV_MODE: str = Field(default="DEVELOPMENT")
    
    # Supabase Relational Credentials
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    
    # Meta Channel Routing Gatekeepers
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_ACCESS_TOKEN: str       # 🔒 Cryptographic Token String Loader
    WHATSAPP_PHONE_NUMBER_ID: str     # 📱 Business Phone ID Node Tracker
    
    # Instruct Pydantic to read directly from the root .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore" # Safely bypasses secondary system variables on Render
    )

# Instantiate a global configuration context for the entire application
settings = Settings()