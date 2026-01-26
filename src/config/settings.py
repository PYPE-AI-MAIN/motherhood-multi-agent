from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LiveKit Configuration
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"
    
    # LLM Configuration
    openai_api_key: str
    
    # Feature Flags
    enable_living_memory: bool = True
    enable_mock_api: bool = True
    
    # Current Date (for testing)
    current_date: str = "2026-01-20"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'


settings = Settings()
