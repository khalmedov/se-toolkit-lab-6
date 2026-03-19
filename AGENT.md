# Agent Documentation

## Overview

`agent.py` is a CLI tool that answers questions about the SE Toolkit project using an LLM with function calling. The agent can read project files, query the live backend API, and execute safe system commands.

## Usage
```bash
uv run agent.py "Your question here"
```

Output is a JSON object:
```json
{
  "answer": "...",
  "source": "wiki/github.md",
  "tool_calls": [
    {"tool": "read_file", "args": {"path": "wiki/github.md"}, "result": "..."}
  ]
}
```

## LLM Provider

The agent uses the Qwen Code API proxy running locally on the VM at `http://localhost:42005/v1`. This provides 1000 free requests per day using the `qwen3-coder-plus` model with strong tool-calling support.

## Environment Variables

All configuration is read from environment variables:

| Variable | Purpose | Source |
|---|---|---|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend base URL | optional, defaults to `http://localhost:42002` |

## Tools

### `read_file`
Reads a file from the project repository. Used for wiki documentation, source code, config files, and ETL pipeline code. Prevents directory traversal attacks by validating paths stay within project root.

### `list_files`
Lists files and directories at a given path. Used to discover available wiki pages and backend modules.

### `query_api`
Sends HTTP requests to the deployed backend API. Returns `status_code` and `body`. Authenticates with `LMS_API_KEY`. Supports optional `no_auth` parameter for testing unauthenticated behavior. Used for live data questions: item counts, analytics, HTTP status codes, endpoint errors.

### `run_command`
Executes safe system commands. Blocked patterns prevent destructive operations. Used for checking service status and system resources.

## Agentic Loop

1. Send question + tool definitions to LLM
2. If LLM responds with tool calls → execute each tool, append results, repeat
3. If LLM responds with text (no tool calls) → output final JSON answer
4. Maximum 20 iterations to prevent infinite loops

## Tool Selection Strategy

The system prompt guides the LLM to choose the right tool:
- Wiki/documentation questions → `read_file("wiki/...")`
- Source code questions → `read_file` on backend files
- Live data (item counts, status codes, analytics) → `query_api`
- Service status → `run_command`
- Directory exploration → `list_files`

## Project Structure Hints

The system prompt includes key paths:
- Backend source: `backend/app/`
- Routers: `backend/app/routers/`
- Wiki docs: `wiki/`

## Lessons Learned

1. **Model selection matters**: OpenRouter free models have 50 req/day limit and frequent rate limits. Qwen Code proxy provides 1000 req/day locally with no rate limits.
2. **File size limits**: Large files need higher read limits (20000 chars) so the LLM finds the answer without re-reading.
3. **System prompt specificity**: Vague tool descriptions cause wrong tool selection. Concrete examples in descriptions improve accuracy significantly.
4. **Retry on 429**: Adding automatic retry with backoff handles temporary rate limits gracefully.
5. **Source field logic**: When both `query_api` and `read_file` are used, prefer `read_file` path as source since it identifies the specific code file.

## Final Eval Score

Local benchmark: **10/10 passed**
