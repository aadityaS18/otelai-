import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from health_api import health
from agent.deep_agent import answer_question

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

    import base64

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
    return health()


@app.post("/api/chat")
async def api_chat(request: Request):
    check_basic_auth(request)

    body = await request.json()
    question = body.get("question", "").strip()

    if not question:
        return JSONResponse({"answer": "Please ask a question."})

    try:
        answer = answer_question(question)
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse(
            {"answer": f"Error: {type(e).__name__}: {str(e)}"},
            status_code=500,
        )


@app.get("/api")
def api_root():
    return {"status": "ok", "message": "Otel AI API running"}