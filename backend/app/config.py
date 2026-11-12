"""The settings sheet.

Everything that can change from one computer to another (addresses, model names,
secret keys) lives here, so the rest of the code never has to hard-code them.
Values come from the `.env` file (or from Docker Compose); anything missing
falls back to the safe default written below.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    app_name: str = "Accument"

    database_url: str = "postgresql+psycopg2://accument:accument@db:5432/accument"

    ollama_url: str = "http://host.docker.internal:11434"

    model_name: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    ollama_timeout: int = 300
    num_ctx: int = 4096  # how much text (in tokens) the model can read at once


    # Login wristbands (JWT tokens)
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24 * 7


    # Where files are kept inside the box
    chroma_path: str = "/data/chroma"
    upload_dir: str = "/data/uploads"
    max_upload_mb: int = 25

    
    retrieve_k: int = 6
    chat_rate_limit: str = "20/minute"


settings = Settings()