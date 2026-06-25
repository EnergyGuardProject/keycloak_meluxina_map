# Team ↔ Slurm token map

A small service that maps teams to their Slurm tokens (encrypted at
rest), and resolves an individual Keycloak user to a token by looking up the
user's team live from the EnergyGuard dashboard's database. It consists of:

- **`api/`** — a FastAPI service in front of the database (API-key protected).
- **`frontend/`** — a very minimal Flask UI to set a team's token.
- **`docker-compose.yml`** — runs both, on the `nginxproxy_energyguard_net`
  network.

## Data store

Data lives in a dedicated `keycloak_slurm_map` database on an
shared `pgdb` Postgres container. The database and its table are created
automatically on first start.

We store the team → token mapping in the database of this service. We do not store which users belong
to a team, that is read from the dashboard database.

Schema (`team_slurm_token`):

| column            | notes                                            |
|-------------------|--------------------------------------------------|
| `team_name`         | unique; matches the dashboard's `Team.name`    |
| `encrypted_token`   | Fernet-encrypted slurm token |
| `created_at` / `updated_at` | timestamps                             |

### Resolving a user → team (source of truth = the dashboard)

This service queries the dashboard DB, by running the following:

```sql
SELECT t.name FROM profile p
JOIN core_user u ON u.id = p.user_id
JOIN team t ON t.id = p.team_id
WHERE u.email = :username;
```

`GET /users/{username}/token` uses this to find the user's current team, then
returns that team's stored token.

All dashboard access goes through `app/teams.py`
(`get_user_team`). It is the only place that touches the dashboard DB, used
by the one endpoint `GET /users/{username}/token`. Every other endpoint uses
only our own `keycloak_slurm_map` DB.

Set `DASHBOARD_DB_ENABLED=false` to disable the lookup (then
`GET /users/{username}/token` returns `400`; the team endpoints still work).

## Encryption

Slurm tokens are encrypted with a symmetric Fernet key (`ENCRYPTION_KEY`)
before being written, and only decrypted in memory when retrieved through the
authenticated token endpoint.

## API

Interactive docs are served at `/docs`.

**Authentication.** Every endpoint except `GET /health` requires the header
`X-API-Key: <API_KEY>`. A missing or wrong key returns `401`. The key is
compared in constant time.

Summary:

| Method & path                          | Purpose                                  | Dashboard DB |
|----------------------------------------|------------------------------------------|:------------:|
| `PUT /teams/{team_name}/token`         | Set/update a team's token (upsert)       | no           |
| `DELETE /teams/{team_name}`            | Delete a team's token                    | no           |
| `GET /teams`                           | List teams (**no tokens**)               | no           |
| `GET /teams/{team_name}/token`         | Retrieve a team's decrypted token        | no           |
| `GET /users/{keycloak_username}/token` | Resolve a user's team → its token        | yes          |
| `GET /health`                          | Health check (no auth)                   | no           |

---

### `PUT /teams/{team_name}/token` — set/update a team's token

Creates the team's token if it does not exist, or updates it if it does
(upsert). This is the only write endpoint and the one the frontend uses.

Request body: `{ "slurm_token": "<string>" }` (required).

Responses: `200` `TeamOut` (no token) · `401` bad key.

```bash
curl -X PUT http://127.0.0.1:${API_PORT}/teams/alpha/token \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"slurm_token":"shared-team-token"}'
```
```json
{ "team_name":"alpha",
  "created_at":"2026-06-18T12:00:00Z", "updated_at":"2026-06-18T12:00:00Z" }
```

---

### `DELETE /teams/{team_name}` — delete a team's token

Responses: `200` `{ "detail": ... }` · `404` if the team has no token · `401`
bad key.

```bash
curl -X DELETE http://127.0.0.1:${API_PORT}/teams/alpha \
  -H "X-API-Key: $API_KEY"
```

---

### `GET /teams` — list teams

Returns all teams that have a token, **without the tokens**. Useful for auditing.

Responses: `200` `[TeamOut, ...]` · `401` bad key.

```json
[ { "team_name":"alpha", "created_at":"...", "updated_at":"..." } ]
```

---

### `GET /teams/{team_name}/token` — retrieve a team's token

Returns the decrypted token for a team. API-key protected; the frontend never
calls it.

Responses: `200` `{ "team_name": ..., "slurm_token": ... }` · `404` if the team
has no token · `401` bad key.

```bash
curl http://127.0.0.1:${API_PORT}/teams/alpha/token -H "X-API-Key: $API_KEY"
```

---

### `GET /users/{keycloak_username}/token` — resolve a user's token

Looks up the user's team **live from the dashboard**, then returns that team's
decrypted token. This is the path the slurm consumer uses.

Responses: `200` `{ "keycloak_username": ..., "team_name": ..., "slurm_token": ... }`
· `404` if the user is in no team, or that team has no token · `400` if dashboard
lookups are disabled · `401` bad key.

```bash
curl http://127.0.0.1:${API_PORT}/users/alice@energy-guard.eu/token \
  -H "X-API-Key: $API_KEY"
```
```json
{ "keycloak_username":"alice@energy-guard.eu",
  "team_name":"alpha", "slurm_token":"shared-team-token" }
```

---

### `GET /health` — health check

No auth. Returns `{ "status": "ok" }`.

## Frontend

A single-page form (team name + slurm token) that calls
`PUT /teams/{team}/token`. It holds the API key **server-side** and never
displays individual user tokens. It is published on **localhost only**, so reach
it via SSH port-forwarding:

```bash
ssh -L ${FRONTEND_PORT}:127.0.0.1:${FRONTEND_PORT} <host>
# then open http://localhost:${FRONTEND_PORT}
```

## Networking / ports

Both services join the external `nginxproxy_energyguard_net` network. Ports are set in
`.env` (`API_PORT`, `FRONTEND_PORT`, `API_BASE_URL`); see `.env.example`:

- API:      `127.0.0.1:${API_PORT}` → container `:${API_PORT}`
- Frontend: `127.0.0.1:${FRONTEND_PORT}` → container `:${FRONTEND_PORT}`

## Running

```bash
cd /mnt/datadisk/keycloak_meluxina_map
# .env already contains generated secrets; review it first.
docker compose up -d --build
docker compose logs -f api
```

`.env` holds all secrets and is git-ignored. See `.env.example` for the keys and
how to regenerate them.
