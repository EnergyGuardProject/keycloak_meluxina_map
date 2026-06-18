"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Postgres (shared pgdb instance on nginxproxy_energyguard_net) ---
    postgres_host: str = "pgdb"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    # Maintenance DB used only to bootstrap-create the application DB.
    postgres_maintenance_db: str = "postgres"
    # The dedicated database that holds the keycloak<->slurm mapping.
    app_db_name: str = "keycloak_slurm_map"

    # --- Security ---
    # Symmetric Fernet key used to encrypt slurm tokens at rest.
    encryption_key: str
    # API key required (via X-API-Key header) for every endpoint.
    api_key: str

    # --- EnergyGuard dashboard DB (READ-ONLY: source of truth for teams) ---
    # Reached over the dashboard's own compose network (see docker-compose.yml).
    # Leave dashboard_db_enabled=false to fall back to the self-contained
    # team_name stored on each row.
    dashboard_db_enabled: bool = True
    dashboard_db_host: str = "db"
    dashboard_db_port: int = 5432
    dashboard_db_name: str = "energyguard"
    dashboard_db_user: str = "energyguard_user"
    dashboard_db_password: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def app_db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.app_db_name}"
        )

    @property
    def maintenance_db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_maintenance_db}"
        )

    @property
    def dashboard_db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.dashboard_db_user}:{self.dashboard_db_password}"
            f"@{self.dashboard_db_host}:{self.dashboard_db_port}/{self.dashboard_db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
