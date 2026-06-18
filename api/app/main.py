"""FastAPI service mapping teams to encrypted Slurm tokens.

This service stores only **team -> slurm token** pairs. A user's team is looked
up live from the EnergyGuard dashboard DB, so there is nothing to keep in sync.

Endpoints (all require the X-API-Key header except /health):
  PUT    /teams/{team_name}/token         Set/update a team's slurm token
  DELETE /teams/{team_name}               Delete a team's slurm token
  GET    /teams                           List teams (no tokens)
  GET    /teams/{team_name}/token         Retrieve a team's decrypted token
  GET    /users/{keycloak_username}/token Resolve a user's team -> team token
"""
import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crypto, teams
from .config import get_settings
from .database import get_db, init_db
from .models import TeamSlurmToken
from .schemas import (
    MessageOut,
    TeamOut,
    TeamTokenOut,
    TeamTokenUpsert,
    UserTokenOut,
)
from .security import require_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Team ↔ Slurm token map",
    description=(
        "Stores encrypted Slurm tokens per team. A user's team is resolved "
        "live from the EnergyGuard dashboard."
    ),
    version="2.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.put(
    "/teams/{team_name}/token",
    response_model=TeamOut,
    dependencies=[Depends(require_api_key)],
)
def upsert_team_token(
    team_name: str, payload: TeamTokenUpsert, db: Session = Depends(get_db)
) -> TeamSlurmToken:
    """Create or update the slurm token for a team."""
    row = (
        db.query(TeamSlurmToken)
        .filter(TeamSlurmToken.team_name == team_name)
        .first()
    )
    encrypted = crypto.encrypt_token(payload.slurm_token)
    if row is None:
        row = TeamSlurmToken(team_name=team_name, encrypted_token=encrypted)
        db.add(row)
    else:
        row.encrypted_token = encrypted
    db.commit()
    db.refresh(row)
    return row


@app.delete(
    "/teams/{team_name}",
    response_model=MessageOut,
    dependencies=[Depends(require_api_key)],
)
def delete_team(team_name: str, db: Session = Depends(get_db)) -> MessageOut:
    """Delete a team's slurm-token mapping."""
    row = (
        db.query(TeamSlurmToken)
        .filter(TeamSlurmToken.team_name == team_name)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    db.delete(row)
    db.commit()
    return MessageOut(detail=f"Deleted token for team '{team_name}'")


@app.get(
    "/teams",
    response_model=list[TeamOut],
    dependencies=[Depends(require_api_key)],
)
def list_teams(db: Session = Depends(get_db)) -> list[TeamSlurmToken]:
    """List teams that have a token. Tokens are intentionally NOT included."""
    return db.query(TeamSlurmToken).order_by(TeamSlurmToken.team_name).all()


@app.get(
    "/teams/{team_name}/token",
    response_model=TeamTokenOut,
    dependencies=[Depends(require_api_key)],
)
def get_team_token(team_name: str, db: Session = Depends(get_db)) -> TeamTokenOut:
    """Retrieve a team's decrypted slurm token."""
    row = (
        db.query(TeamSlurmToken)
        .filter(TeamSlurmToken.team_name == team_name)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    return TeamTokenOut(
        team_name=team_name,
        slurm_token=crypto.decrypt_token(row.encrypted_token),
    )


@app.get(
    "/users/{keycloak_username}/token",
    response_model=UserTokenOut,
    dependencies=[Depends(require_api_key)],
)
def get_user_token(
    keycloak_username: str, db: Session = Depends(get_db)
) -> UserTokenOut:
    """Resolve a user's team from the dashboard and return that team's token.

    This is the path the slurm consumer uses. The user's team is read live from
    the dashboard, so it always reflects current membership.
    """
    if not get_settings().dashboard_db_enabled:
        raise HTTPException(
            status_code=400, detail="Dashboard DB lookups are disabled"
        )

    team_name = teams.get_user_team(keycloak_username)
    if team_name is None:
        raise HTTPException(
            status_code=404,
            detail=f"User '{keycloak_username}' is not in any team",
        )

    row = (
        db.query(TeamSlurmToken)
        .filter(TeamSlurmToken.team_name == team_name)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No token set for team '{team_name}'",
        )
    return UserTokenOut(
        keycloak_username=keycloak_username,
        team_name=team_name,
        slurm_token=crypto.decrypt_token(row.encrypted_token),
    )
