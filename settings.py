from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_TOKEN: str = ""
    BASE_URL: str = ""
    USERNAME: str = ""
    model_config = SettingsConfigDict(env_file=".env")
