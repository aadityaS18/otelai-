## Revenue Manager Agent

This project includes a local Revenue Manager Agent for hotel commercial analysis.

The agent can answer natural-language questions about:

- OTB summary
- Segment mix
- Pickup pace
- Block vs transient mix
- Point-in-time as-of OTB with approval

Revenue numbers come from deterministic Python tools backed by database views. The local LLM is used for conversation, tool routing, and explanation.

## Local Model

This project uses Ollama for local development, so no paid OpenAI API is required.

Install/pull the local model:

```bash
ollama pull qwen2.5:3b