import os
import sys
import base64
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from health_api import get_health_payload
from tools.revenue_tools import (
    get_otb_summary,
    get_segment_mix,
    get_pickup_delta,
    get_as_of_otb,
    get_block_vs_transient_mix,
)

app = FastAPI(title="Otel AI Revenue Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_basic_auth(request: Request):
    expected_user = os.getenv("BASIC_AUTH_USERNAME", "admin")
    expected_pass = os.getenv("BASIC_AUTH_PASSWORD", "otel-demo")

    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        decoded = base64.b64decode(auth.split(" ")[1]).decode()
        username, password = decoded.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if username != expected_user or password != expected_pass:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/health")
def api_health(request: Request):
    check_basic_auth(request)
    return get_health_payload()


def answer_question(question: str) -> str:
    q = question.lower()

    if "as of" in q:
        result = get_as_of_otb(
            stay_month="2026-07",
            as_of_utc="2026-06-15T00:00:00+00:00",
            exclude_cancelled=True,
        )
        return f"July 2026 OTB as of 2026-06-15 was ${result.get('total_revenue', result)}."

    if "pickup" in q:
        result = get_pickup_delta(
            booking_window_days=7,
            future_stay_from="2026-06-15",
        )
        return (
            f"Pickup in the last 7 days: {result['new_reservations']} reservations, "
            f"{result['new_room_nights']} room nights, and "
            f"${result['new_total_revenue']:,.0f} total revenue.\n\n"
            f"Main driver: {result['by_segment'][0]['market_name']}."
        )

    if "segment" in q or "ota" in q:
        result = get_segment_mix(stay_month="2026-07", macro_group=None)
        rows = result.get("segments", result)
        return f"July 2026 segment mix:\n\n{rows}"

    if "block" in q or "transient" in q:
        result = get_block_vs_transient_mix(stay_month="2026-07")
        return (
            f"Block vs transient mix for July 2026:\n\n"
            f"{result}"
        )

    result = get_otb_summary(stay_month="2026-07", exclude_cancelled=True)
    return f"July 2026 OTB is ${result.get('total_revenue', result):,.0f}."


@app.post("/api/chat")
async def api_chat(request: Request):
    check_basic_auth(request)

    body = await request.json()
    question = body.get("question", "").strip()

    if not question:
        return JSONResponse({"answer": "Please ask a question."})

    try:
        return JSONResponse({"answer": answer_question(question)})
    except Exception as e:
        return JSONResponse(
            {"answer": f"Error: {type(e).__name__}: {str(e)}"},
            status_code=500,
        )


@app.get("/api")
def api_root():
    return {"status": "ok", "message": "Otel AI API running"}