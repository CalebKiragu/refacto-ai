from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    app_env: str = "development"
    github_webhook_secret: str
    github_app_id: str
    github_client_id: str
    github_client_secret: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: str
    postgres_db: str
    redis_url: str
    openai_api_key: str
    database_url: str
    
    class Config:
        env_file = ".env"

settings = Settings()