"""Pydantic request/response schemas.

Slurm tokens are accepted in requests and only ever returned by the explicit
token-retrieval endpoints (API-key protected); listing endpoints never include
them.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TeamTokenUpsert(BaseModel):
    slurm_token: str = Field(..., min_length=1)
    meluxina_project_name: str = Field(..., min_length=1)


class TeamOut(BaseModel):
    """A team's mapping WITHOUT the token (safe to list)."""

    team_name: str
    meluxina_project_name: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TeamTokenOut(BaseModel):
    """A team's decrypted slurm token."""

    team_name: str
    meluxina_project_name: Optional[str]
    slurm_token: str


class UserTokenOut(BaseModel):
    """The decrypted slurm token resolved for a single user via their team."""

    keycloak_username: str
    team_name: str
    meluxina_project_name: Optional[str]
    slurm_token: str


class MessageOut(BaseModel):
    detail: str
