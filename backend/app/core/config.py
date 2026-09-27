from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    DATABASE_URL: str

    SECRET_KEY: str

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    GOVERNMENT_USERNAME: str

    GOVERNMENT_PASSWORD: str

    ROUTING_BASE_URL: str = 'https://routing.openstreetmap.de/routed-car'
    GEOCODING_BASE_URL: str = 'https://photon.komoot.io'
    MAP_USER_AGENT: str = 'UrbanIQ-RoutePlanner/1.0 (https://github.com/shrim486/SIH-26124)'

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
