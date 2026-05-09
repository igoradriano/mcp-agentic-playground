# MCP Agentic Playground

A Python portfolio project that demonstrates Agentic AI workflows using MCP (Model Context Protocol).

This repository shows how to:
- expose tools/resources/prompts through MCP servers
- consume MCP from native clients and OpenAI Agents SDK
- build a Streamlit chat UI that performs tool-calling through MCP

## Why This Matters for Agentic AI Roles

This project demonstrates practical skills expected in Agentic AI Engineer positions:
- tool orchestration with MCP
- multi-entrypoint architecture (CLI + SDK + UI)
- environment-driven configuration
- reproducible local setup for fast onboarding

## Project Structure

- `classes/`: reusable client components (`mcp_client.py`, `llm_client.py`)
- `servers/`: MCP servers (`server_test.py`, `server_sql.py`)
- `cliente_nativo/`: native MCP usage examples
- `cliente_openai/`: OpenAI Agents SDK + MCP example
- `streamlit/`: chat UI integrated with MCP tools

## Architecture

```mermaid
flowchart LR
    User --> UI[Streamlit Chat]
    UI --> LLM[OpenAI Chat Completions]
    LLM -->|tool calls| MCPClient[MCP Client]
    MCPClient --> MCPServer[MCP Server]
    MCPServer --> SQL[(PostgreSQL)]
    MCPServer --> Resource[(File/Memory Resource)]
```

## Quickstart (Fresh Machine)

### 1. Clone and enter project

```bash
git clone <your-repo-url>
cd mcp-agentic-playground
```

### 2. Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned)
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
copy .env.example .env
```

Then update `OPENAI_API_KEY` in `.env`.

## Run Demos

### A. Run demo MCP server (SSE)

```bash
mcp run servers/server_test.py
```

### B. Native MCP client example

```bash
python cliente_nativo/client_example.py
```

### C. OpenAI Agents + MCP example

```bash
python cliente_openai/chat_agent_example.py
```

### D. Streamlit chat app

```bash
streamlit run streamlit/chat.py
```

## UI Preview

![Streamlit UI preview](arquivos/novadrive.png)

## Configuration Notes

- `server_sql.py` supports environment overrides via:
  - `MCP_SQL_HOST`
  - `MCP_SQL_PORT`
  - `MCP_SQL_DATABASE`
  - `MCP_SQL_USER`
  - `MCP_SQL_PASSWORD`
- Public demo DB defaults are kept for portfolio convenience.

## Known Limitations

- No CI pipeline yet.
- No automated tests yet (only manual smoke checks).
- SQL tool currently executes raw SQL and should be constrained for production use.

## Suggested Next Steps

1. Add smoke tests for tools/resources/prompts.
2. Add CI (lint + smoke test) on pull requests.
3. Add screenshots/GIF of Streamlit flow for recruiter-first visualization.

## License

MIT. See [LICENSE](LICENSE).
