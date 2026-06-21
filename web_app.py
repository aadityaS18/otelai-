import json
import os
import secrets
import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Generator

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from starlette.status import HTTP_401_UNAUTHORIZED

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.deep_agent import build_agent_config


app = FastAPI(title="Otel AI Revenue Manager Agent")
security = HTTPBasic()

LOAD_PROOF_PATH = Path("etl/LOAD_PROOF.json")


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    expected_user = get_env("BASIC_AUTH_USERNAME", "admin")
    expected_password = get_env("BASIC_AUTH_PASSWORD", "otel-demo")

    username_ok = secrets.compare_digest(credentials.username, expected_user)
    password_ok = secrets.compare_digest(credentials.password, expected_password)

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


def get_database_url() -> str:
    database_url = get_env("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing.")

    return database_url


def get_message_content(message) -> str:
    content = getattr(message, "content", None)

    if isinstance(content, list):
        return "\n".join(
            part.get("text", str(part)) if isinstance(part, dict) else str(part)
            for part in content
        )

    return content or str(message)


def needs_as_of_approval(question: str) -> bool:
    q = question.lower()
    return "as of" in q or "point in time" in q or "point-in-time" in q


def infer_skill_route(question: str) -> str:
    q = question.lower()

    if "as of" in q or "point in time" in q or "point-in-time" in q:
        return "Skill: otb_briefing / point-in-time approval path → Tool: get_as_of_otb"

    if "pickup" in q or "pace" in q:
        return "Skill: pickup_pace → Tool: get_pickup_delta"

    if "ota" in q or "dependency" in q:
        return "Skill: ota_dependency → Tool: get_segment_mix"

    if "segment" in q or "mix" in q:
        return "Skill: segment_mix → Tool: get_segment_mix"

    if "block" in q or "transient" in q or "group" in q:
        return "Skill: block_mix → Tool: get_block_vs_transient_mix"

    if "briefing" in q or "recommend" in q or "risk" in q:
        return "Skill: commercial_recommendation → Tools selected by question"

    return "Skill: otb_briefing → Tool: get_otb_summary"


@lru_cache(maxsize=1)
def get_agent():
    groq_api_key = get_env("GROQ_API_KEY")

    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY is missing.")

    os.environ["GROQ_API_KEY"] = groq_api_key

    config = build_agent_config()

    llm = ChatGroq(
        model=get_env("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=0,
    )

    agent = create_react_agent(
        model=llm,
        tools=config["tools"],
        checkpointer=MemorySaver(),
        prompt=config["system_prompt"],
    )

    return agent


def extract_tool_trace(result: dict) -> list[str]:
    trace = []

    for msg in result.get("messages", []):
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            for call in tool_calls:
                trace.append(f"Tool called: {call.get('name')} args={call.get('args')}")

        msg_type = getattr(msg, "type", "")
        name = getattr(msg, "name", None)
        content = getattr(msg, "content", "")

        if msg_type == "tool":
            trace.append(f"Tool result from: {name}")
            if content:
                trace.append(f"Tool output: {content}")

    return trace


def sse(event: str, data: str) -> str:
    safe_data = str(data).replace("\r", "").replace("\n", "\\n")
    return f"event: {event}\ndata: {safe_data}\n\n"


def run_agent_stream(question: str, approved: bool, thread_id: str) -> Generator[str, None, None]:
    if needs_as_of_approval(question) and not approved:
        yield sse(
            "error",
            "This question needs approval before using the point-in-time OTB tool.",
        )
        return

    yield sse("trace", infer_skill_route(question))
    yield sse("trace", "Running LangGraph agent...")

    try:
        agent = get_agent()

        result = agent.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        )

        trace = extract_tool_trace(result)

        for item in trace:
            yield sse("trace", item)

        answer = get_message_content(result["messages"][-1])
        yield sse("answer", answer)
        yield sse("done", "done")

    except Exception as exc:
        yield sse("error", f"Agent error: {str(exc)}")


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
def index(_: str = Depends(require_auth)):
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Otel AI Revenue Manager Agent</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <style>
    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 35%),
        linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
      color: #0f172a;
    }

    .page {
      max-width: 1180px;
      margin: 0 auto;
      padding: 34px 22px;
    }

    .hero {
      background: linear-gradient(135deg, #111827 0%, #1e3a8a 100%);
      color: white;
      padding: 34px;
      border-radius: 24px;
      box-shadow: 0 22px 50px rgba(15, 23, 42, 0.22);
      margin-bottom: 22px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.18);
      font-size: 13px;
      margin-bottom: 18px;
    }

    .hero h1 {
      font-size: 38px;
      line-height: 1.1;
      margin: 0;
      letter-spacing: -0.04em;
    }

    .hero p {
      margin: 14px 0 0;
      color: #dbeafe;
      max-width: 720px;
      font-size: 16px;
      line-height: 1.6;
    }

    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
      gap: 22px;
    }

    .card {
      background: rgba(255,255,255,0.9);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(226, 232, 240, 0.9);
      border-radius: 22px;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
      padding: 24px;
    }

    .card h2 {
      margin: 0 0 12px;
      font-size: 19px;
      letter-spacing: -0.02em;
    }

    .quick {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }

    .quick button {
      background: #f8fafc;
      color: #0f172a;
      border: 1px solid #dbe3ef;
      border-radius: 14px;
      padding: 13px 14px;
      cursor: pointer;
      font-weight: 700;
      text-align: left;
      transition: all 0.15s ease;
    }

    .quick button:hover {
      border-color: #2563eb;
      background: #eff6ff;
      transform: translateY(-1px);
    }

    textarea {
      width: 100%;
      min-height: 118px;
      font-size: 15px;
      line-height: 1.5;
      padding: 15px;
      border: 1px solid #cbd5e1;
      border-radius: 16px;
      resize: vertical;
      outline: none;
      color: #0f172a;
      background: white;
    }

    textarea:focus {
      border-color: #2563eb;
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
    }

    .primary {
      margin-top: 14px;
      width: 100%;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: white;
      border: none;
      padding: 15px 18px;
      border-radius: 16px;
      cursor: pointer;
      font-weight: 800;
      font-size: 15px;
      box-shadow: 0 12px 24px rgba(37, 99, 235, 0.24);
    }

    .primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 16px 30px rgba(37, 99, 235, 0.3);
    }

    .output {
      min-height: 210px;
      white-space: pre-wrap;
      line-height: 1.65;
      color: #111827;
      background: #ffffff;
      border-radius: 16px;
      border: 1px solid #e2e8f0;
      padding: 18px;
    }

    .trace {
      min-height: 210px;
      white-space: pre-wrap;
      line-height: 1.55;
      background: #020617;
      color: #dbeafe;
      border-radius: 16px;
      padding: 18px;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 13px;
      overflow-x: auto;
    }

    .meta {
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }

    .metric {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 14px;
    }

    .metric strong {
      display: block;
      color: #0f172a;
      margin-bottom: 4px;
    }

    .metric span {
      color: #64748b;
      font-size: 14px;
    }

    .status {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #16a34a;
      font-weight: 800;
      margin-bottom: 10px;
    }

    .dot {
      width: 9px;
      height: 9px;
      background: #22c55e;
      border-radius: 50%;
      box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.12);
    }

    .small {
      color: #64748b;
      font-size: 14px;
      line-height: 1.5;
    }

    @media (max-width: 860px) {
      .grid {
        grid-template-columns: 1fr;
      }

      .hero h1 {
        font-size: 30px;
      }

      .quick {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>
  <div class="page">
    <section class="hero">
      <div class="badge">LangGraph Agent · Revenue Tools · Hosted Postgres</div>
      <h1>Otel AI Revenue Manager Agent</h1>
      <p>
        Ask commercial questions about OTB, pickup pace, segment mix, OTA dependency,
        and block versus transient demand. The interface streams the answer and shows
        tool / skill activity for auditability.
      </p>
    </section>

    <div class="grid">
      <div class="card">
        <h2>Ask the agent</h2>

        <div class="quick">
          <button onclick="setQ('What is July 2026 OTB?')">July 2026 OTB</button>
          <button onclick="setQ('What is our segment mix for July 2026?')">Segment Mix</button>
          <button onclick="setQ('How much pickup did we get in the last 7 days for future stays from 2026-06-15?')">Pickup Delta</button>
          <button onclick="setQ('What is block vs transient mix for July 2026?')">Block vs Transient</button>
          <button onclick="setQ('What was July 2026 OTB as of 2026-06-15?')">As-of OTB</button>
          <button onclick="setQ('Give me a revenue manager briefing for July 2026.')">RM Briefing</button>
        </div>

        <textarea id="question">What is July 2026 OTB?</textarea>
        <button class="primary" onclick="askAgent()">Run LangGraph Agent</button>

        <div class="meta">
          <div class="metric">
            <strong>Approval Gate</strong>
            <span>Point-in-time OTB questions require human approval before the tool runs.</span>
          </div>
          <div class="metric">
            <strong>Deterministic Tools</strong>
            <span>Revenue metrics are calculated from Postgres, not guessed by the model.</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="status"><span class="dot"></span> Live agent UI</div>
        <p class="small">
          This UI calls the deployed FastAPI backend, streams events, and displays
          the selected skill route, tool call, arguments, and tool output.
        </p>

        <h2>Tool / Skill Trace</h2>
        <div id="trace" class="trace">Trace will appear here.</div>
      </div>
    </div>

    <div class="card" style="margin-top: 22px;">
      <h2>Answer</h2>
      <div id="answer" class="output">Answer will appear here.</div>
    </div>
  </div>

<script>
  const threadId = "web-" + crypto.randomUUID();

  function setQ(text) {
    document.getElementById("question").value = text;
  }

  async function askAgent() {
    const question = document.getElementById("question").value;
    const answerBox = document.getElementById("answer");
    const traceBox = document.getElementById("trace");

    answerBox.textContent = "Thinking...";
    traceBox.textContent = "";

    let approved = false;

    const qLower = question.toLowerCase();
    if (qLower.includes("as of") || qLower.includes("point in time") || qLower.includes("point-in-time")) {
      approved = confirm("This question uses point-in-time OTB. Approve tool call?");
      if (!approved) {
        answerBox.textContent = "Cancelled. As-of OTB tool was not run.";
        traceBox.textContent = "Human approval denied. Tool was not called.";
        return;
      }
    }

    const response = await fetch("/chat_stream/", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        question: question,
        approved: approved,
        thread_id: threadId
      })
    });

    if (!response.ok) {
      answerBox.textContent = "Request failed: " + response.status;
      traceBox.textContent = "The backend route returned HTTP " + response.status + ". Check Render logs.";
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    answerBox.textContent = "";

    while (true) {
      const {value, done} = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {stream: true});
      const parts = buffer.split("\\n\\n");
      buffer = parts.pop();

      for (const part of parts) {
        const lines = part.split("\\n");
        let eventType = "";
        let data = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.replace("event: ", "");
          }
          if (line.startsWith("data: ")) {
            data = line.replace("data: ", "").replaceAll("\\\\n", "\\n");
          }
        }

        if (eventType === "trace") {
          traceBox.textContent += data + "\\n\\n";
        }

        if (eventType === "answer") {
          answerBox.textContent = data;
        }

        if (eventType === "error") {
          answerBox.textContent = data;
        }
      }
    }
  }
</script>
</body>
</html>
    """


@app.post("/chat_stream")
@app.post("/chat_stream/")
async def chat_stream(request: Request, _: str = Depends(require_auth)):
    body = await request.json()

    question = body.get("question", "").strip()
    approved = bool(body.get("approved", False))
    thread_id = body.get("thread_id") or f"web-{uuid.uuid4()}"

    if not question:
        return JSONResponse({"error": "Question is required."}, status_code=400)

    return StreamingResponse(
        run_agent_stream(question, approved, thread_id),
        media_type="text/event-stream",
    )


@app.get("/health")
def health(_: str = Depends(require_auth)):
    proof = load_proof()

    try:
        with psycopg.connect(get_database_url()) as conn:
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

    dataset_revision = manifest_row[0] if manifest_row else proof.get("dataset_revision")
    row_hash = manifest_row[1] if manifest_row else proof.get("load_manifest_row_hash")

    return {
        "status": "ok",
        "db_fingerprint": proof.get("reservation_stay_status_sha256"),
        "dataset_revision": dataset_revision,
        "row_hash": row_hash,
        "financial_status_posted_only_rows": proof.get("aggregates", {}).get("posted_stay_rows"),
        "reservations_hackathon_rows": reservations_hackathon_rows,
    }