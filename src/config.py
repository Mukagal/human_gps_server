from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET:str
    JWT_ALGORITHM:str
    REFRESH_TOKEN_EXPIRY:int = 7 
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

Config = Settings()