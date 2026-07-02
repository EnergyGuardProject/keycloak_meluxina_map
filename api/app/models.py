"""SQLAlchemy models.

This service stores only the **team -> slurm token** mapping. Which users belong
to a team is never stored here: it is read live from the EnergyGuard dashboard
DB (the source of truth), so the two databases can never drift out of sync.
"""
from sqlalchemy import Column, DateTime, Integer, String, func

from .database import Base


class TeamSlurmToken(Base):
    __tablename__ = "team_slurm_token"

    id = Column(Integer, primary_key=True)
    # Team name (matches the dashboard's Team.name, which is unique).
    team_name = Column(String(255), unique=True, nullable=False, index=True)
    # Fernet-encrypted slurm token. Never stored or logged in plaintext.
    encrypted_token = Column(String, nullable=False)
    # MeluXina project name the team's jobs run under. Set by the admin
    # alongside the token; nullable so pre-existing rows migrate cleanly.
    meluxina_project_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
