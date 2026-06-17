# Revenue Manager Agent Demo

## Current Status

The project now has a local LangGraph + Ollama Revenue Manager Agent that answers natural-language hotel revenue questions using deterministic revenue tools.

No paid OpenAI API is required for local development.

## Model and Framework

- Local model: Ollama `llama3.1:8b`
- Agent framework: LangGraph
- Tool-calling agent: `create_react_agent`
- Memory: LangGraph `MemorySaver`
- Revenue numbers: returned by deterministic Python tools backed by database views

## Working Capabilities

- OTB summary
- Segment mix
- Pickup pace
- Block vs transient mix
- Point-in-time as-of OTB with approval gate
- Visible tool trace in CLI
- Thread continuity in one CLI session
- Local free model development path

## Run

```bash
python scripts/langgraph_agent_cli.py


## UI Demo

Run:

```bash
streamlit run app.py