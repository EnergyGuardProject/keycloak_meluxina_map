"""Read-only access to the EnergyGuard dashboard database for team membership.

The dashboard is the source of truth for teams. A team is `team.name` (unique);
users belong to a team via `profile.team_id`, and the username is the user's
email (`core_user.email`). We reach the dashboard DB over its own compose
network (declared as external in docker-compose.yml) exactly like the dashboard
`web` service does — we only ever SELECT here, never write.
"""
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import get_settings

logger = logging.getLogger(__name__)

# Lazily-created, read-only engine for the dashboard DB.
_dashboard_engine: Engine | None = None


def _engine() -> Engine:
    global _dashboard_engine
    if _dashboard_engine is None:
        _dashboard_engine = create_engine(
            get_settings().dashboard_db_url,
            pool_pre_ping=True,
            # Defensive: never hold writes open against the dashboard DB.
            execution_options={"postgresql_readonly": True},
        )
    return _dashboard_engine


def get_user_team(username: str) -> str | None:
    """Return the team name a user (email) belongs to, or None."""
    query = text(
        """
        SELECT t.name
        FROM profile p
        JOIN core_user u ON u.id = p.user_id
        JOIN team t ON t.id = p.team_id
        WHERE u.email = :username
        """
    )
    with _engine().connect() as conn:
        row = conn.execute(query, {"username": username}).fetchone()
    return row[0] if row else None
