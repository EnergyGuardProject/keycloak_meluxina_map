"""Very minimal frontend for setting a team's slurm token.

Intentionally tiny: a single page with a form for (team name, slurm token).
It holds the API key server-side and forwards the request to the API's
`PUT /teams/{team}/token` endpoint. Individual user tokens are NEVER shown or
handled here. This service is meant to be reached only via port-forwarding, so
it is published on localhost in docker-compose, not on the public internet.
"""
import os

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FRONTEND_SECRET", os.urandom(24).hex())

API_BASE_URL = os.environ.get("API_BASE_URL", "http://keycloak-slurm-api:27431")
API_KEY = os.environ.get("API_KEY", "")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/set-team-token", methods=["POST"])
def set_team_token():
    team_name = (request.form.get("team_name") or "").strip()
    slurm_token = (request.form.get("slurm_token") or "").strip()

    if not team_name or not slurm_token:
        flash("Both team name and slurm token are required.", "error")
        return redirect(url_for("index"))

    try:
        resp = requests.put(
            f"{API_BASE_URL}/teams/{team_name}/token",
            json={"slurm_token": slurm_token},
            headers={"X-API-Key": API_KEY},
            timeout=15,
        )
    except requests.RequestException as exc:
        flash(f"Could not reach the API: {exc}", "error")
        return redirect(url_for("index"))

    if resp.status_code == 200:
        flash(f"Saved slurm token for team '{team_name}'.", "success")
    elif resp.status_code == 401:
        flash("Frontend is not authorised against the API (check API_KEY).", "error")
    else:
        flash(f"API error ({resp.status_code}): {resp.text}", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=27432)
