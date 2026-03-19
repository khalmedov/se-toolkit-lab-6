# Task 3: The System Agent — Implementation Plan

## Overview
Extend the agent from Task 2 by adding a `query_api` tool that allows the agent to query the deployed backend API in addition to reading files.

## query_api Tool Schema
The tool accepts three parameters:
- `method` (string, required): HTTP method — GET, POST, PUT, DELETE
- `path` (string, required): API path e.g. `/items/`, `/analytics/completion-rate?lab=lab-99`
- `body` (string, optional): JSON string body for POST/PUT requests
- `no_auth` (boolean, optional): Send request without Authorization header

Returns JSON with `status_code` and `body`.

## Authentication
- `LMS_API_KEY` is read from `.env.docker.secret` via `load_dotenv`
- Passed as `Authorization: Bearer <key>` header
- Never hardcoded — always from environment variables

## System Prompt Strategy
The agent uses tool selection guidelines:
- Wiki/docs questions → `read_file` / `list_files`
- Source code questions → `read_file`
- Live data questions (item counts, status codes, analytics) → `query_api`
- System status → `run_command`

## Environment Variables
All config from environment variables:
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` from `.env.agent.secret`
- `LMS_API_KEY`, from `.env.docker.secret`
- `AGENT_API_BASE_URL` defaults to `http://localhost:42002`

## Benchmark Results
Initial score: 0/10 (syntax error in agent.py)
After fixes: 10/10 passed

### Issues encountered
1. agent.py had duplicate code — fixed by rewriting from scratch
2. LLM_API_BASE environment variable was overriding dotenv — fixed with `/v1` suffix check
3. OpenRouter free models rate-limited — switched to Qwen Code proxy
4. Agent read files repeatedly without giving final answer — increased max_iterations and improved system prompt
5. query_api always sent auth header — added `no_auth` parameter for unauthenticated testing

## Iteration Strategy
- Test each failing question with `uv run run_eval.py --index N`
- Add specific instructions to system prompt for each failure pattern
- Increase file read limit from 8000 to 20000 chars for large files
