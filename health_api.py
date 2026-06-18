import json
import os
import secrets
from pathlib import Path

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5432/hotel_hackathon",
)

BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "otel-demo")

LOAD_PROOF_PATH = Path("etl/LOAD_PROOF.json")

app = FastAPI(title="Revenue Manager Agent Health")
security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    username_ok = secrets.compare_digest(credentials.username, BASIC_AUTH_USERNAME)
    password_ok = secrets.compare_digest(credentials.password, BASIC_AUTH_PASSWORD)

    if not username_ok or not password_ok:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def load_proof() -> dict:
    if not LOAD_PROOF_PATH.exists():
        return {}

    return json.loads(LOAD_PROOF_PATH.read_text(encoding="utf-8"))


@app.get("/health")
def health(_: str = Depends(require_auth)):
    proof = load_proof()

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("select count(*) from reservations_hackathon")
                reservations_hackathon_rows = cur.fetchone()[0]

                cur.execute(
                    """
                    select dataset_revision, row_hash
                    from load_manifest
                    order by scraped_at desc
                    limit 1
                    """
                )
                manifest_row = cur.fetchone()

    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(exc),
            },
        )

    dataset_revision = manifest_row[0] if manifest_row else None
    row_hash = manifest_row[1] if manifest_row else None

    return {
        "status": "ok",
        "db_fingerprint": proof.get("reservation_stay_status_sha256"),
        "dataset_revision": dataset_revision,
        "row_hash": row_hash,
        "financial_status_posted_only_rows": proof.get("aggregates", {}).get(
            "posted_stay_rows"
        ),
        "reservations_hackathon_rows": reservations_hackathon_rows,
        "load_proof": {
            "dataset_revision": proof.get("dataset_revision"),
            "row_hash": proof.get("load_manifest_row_hash"),
            "posted_stay_rows": proof.get("aggregates", {}).get("posted_stay_rows"),
            "manifest_valid": proof.get("scrape_manifest_check", {}).get(
                "manifest_valid"
            ),
        },
    }