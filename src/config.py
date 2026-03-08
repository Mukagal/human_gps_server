from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET:str
    JWT_ALGORITHM:str
    REFRESH_TOKEN_EXPIRY:int = 7 


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

Config = Settings()