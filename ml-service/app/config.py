from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    webhook_url: str = ""
    mtl_lat: float = 45.5017
    mtl_lon: float = -73.5673
    timezone: str = "America/Toronto"
    min_weeks_ml: int = 8
    data_dir: str = "data"


settings = Settings()
