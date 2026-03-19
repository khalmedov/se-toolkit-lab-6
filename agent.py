#!/usr/bin/env python3
"""
Agent CLI for calling LLM with tools.
Usage: uv run agent.py "Your question here"
"""

import os
import sys
import json
import requests
import subprocess
import shlex
from dotenv import load_dotenv
import argparse
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env.agent.secret', override=True)
load_dotenv(Path(__file__).parent / '.env.docker.secret', override=True)

LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE', '').rstrip('/')
if LLM_API_BASE and not LLM_API_BASE.endswith('/v1'):
    LLM_API_BASE = LLM_API_BASE + '/v1'
LLM_MODEL = os.getenv('LLM_MODEL')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
LMS_API_KEY = os.getenv('LMS_API_KEY')

if not LLM_API_KEY or not LLM_API_BASE or not LLM_MODEL:
    print("ERROR: Missing required environment variables", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.absolute()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file from the project repository. "
                "Use this to read wiki documentation, source code, config files "
                "(e.g. docker-compose.yml, Dockerfile), and ETL pipeline code. "
                "For documentation/wiki questions always use read_file, not query_api."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and directories at a given path in the project repository. "
                "Use this to explore directory structure, find source code files, "
                "or discover available wiki pages and backend modules."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki', 'backend/routers')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a safe system command on the VM. "
                "Use for checking service status (docker ps), viewing logs, "
                "or monitoring system resources (df -h, free -m). "
                "Do NOT use for reading project files — use read_file instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute (e.g., 'docker ps', 'ls -la', 'df -h')"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 10)",
                        "default": 10
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": (
                "Send an HTTP request to the deployed backend API and return the response. "
                "Use this for ALL questions that require live data from the running system: "
                "item counts, analytics, completion rates, top learners, HTTP status codes, "
                "API errors, endpoint responses. "
                "Examples: 'how many items are in the database' -> GET /items/, "
                "'completion rate for lab-99' -> GET /analytics/completion-rate?lab=lab-99. "
                "Do NOT use read_file for these — query the live API."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE",
                        "enum": ["GET", "POST", "PUT", "DELETE"]
                    },
                    "path": {
                        "type": "string",
                        "description": "API path e.g. /items/, /analytics/completion-rate?lab=lab-99"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON string body for POST/PUT requests"
                    },
                    "no_auth": {
                        "type": "boolean",
                        "description": "Set to true to send request WITHOUT Authorization header (to test unauthenticated behavior)"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]


def read_file(path):
    try:
        requested_path = (PROJECT_ROOT / path).resolve()
        if not str(requested_path).startswith(str(PROJECT_ROOT)):
            return "Error: Access denied (path outside project directory)"
        if not requested_path.exists():
            return f"Error: File not found: {path}"
        if not requested_path.is_file():
            return f"Error: Not a file: {path}"
        content = requested_path.read_text(encoding='utf-8')
        if len(content) > 20000:
            content = content[:20000] + f"\n... [truncated, total {len(content)} chars]"
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


def list_files(path):
    try:
        requested_path = (PROJECT_ROOT / path).resolve()
        if not str(requested_path).startswith(str(PROJECT_ROOT)):
            return "Error: Access denied (path outside project directory)"
        if not requested_path.exists():
            return f"Error: Path not found: {path}"
        if not requested_path.is_dir():
            return f"Error: Not a directory: {path}"
        items = []
        for item in sorted(requested_path.iterdir()):
            items.append(f"{'[DIR]' if item.is_dir() else '[FILE]'} {item.name}")
        return "\n".join(items) if items else "(empty directory)"
    except Exception as e:
        return f"Error listing files: {str(e)}"


def run_command(command, timeout=10):
    forbidden_patterns = [
        'rm -rf', 'sudo', 'dd', 'mkfs', 'format',
        '>', '>>', '|', ';', '&&', '||',
        'chmod', 'chown', 'kill', 'pkill',
        'reboot', 'shutdown', 'init', 'systemctl'
    ]
    command_lower = command.lower()
    for pattern in forbidden_patterns:
        if pattern in command_lower:
            return f"Error: Command contains forbidden pattern '{pattern}'. Blocked for security."
    try:
        args = shlex.split(command)
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        output = f"Exit code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return f"Error: Command not found: '{command}'"
    except Exception as e:
        return f"Error executing command: {str(e)}"


def query_api(method="GET", path="/", body=None, no_auth=False):
    headers = {'Content-Type': 'application/json'}
    if LMS_API_KEY and not no_auth:
        headers['Authorization'] = f'Bearer {LMS_API_KEY}'
    url = f"{AGENT_API_BASE_URL}{path}"
    try:
        response = requests.request(method=method.upper(), url=url, headers=headers, data=body, timeout=10)
        try:
            body_data = response.json()
        except Exception:
            body_data = response.text
        return json.dumps({"status_code": response.status_code, "body": body_data}, ensure_ascii=False, indent=2)
    except requests.exceptions.ConnectionError as e:
        return json.dumps({"status_code": 0, "body": f"Connection error: {str(e)}"})
    except requests.exceptions.Timeout:
        return json.dumps({"status_code": 0, "body": "Request timed out after 10 seconds"})
    except Exception as e:
        return json.dumps({"status_code": 0, "body": f"Unexpected error: {str(e)}"})


def execute_tool(tool_call):
    tool_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])
    if tool_name == 'read_file':
        result = read_file(args['path'])
    elif tool_name == 'list_files':
        result = list_files(args['path'])
    elif tool_name == 'run_command':
        result = run_command(args['command'], args.get('timeout', 10))
    elif tool_name == 'query_api':
        result = query_api(method=args.get('method', 'GET'), path=args.get('path', '/'), body=args.get('body'), no_auth=args.get('no_auth', False))
    else:
        result = f"Error: Unknown tool {tool_name}"
    return {"role": "tool", "tool_call_id": tool_call['id'], "name": tool_name, "content": result}


def call_llm(messages, tools=None):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LLM_API_KEY.strip()}'
    }
    data = {'model': LLM_MODEL, 'messages': messages}
    if tools:
        data['tools'] = tools
        data['tool_choice'] = 'auto'
    print(f"\nDEBUG - Request URL: {LLM_API_BASE}/chat/completions", file=sys.stderr)
    try:
        for attempt in range(5):
            response = requests.post(f"{LLM_API_BASE}/chat/completions", headers=headers, json=data, timeout=60)
            print(f"DEBUG - Response status: {response.status_code}", file=sys.stderr)
            if response.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"DEBUG - Rate limited, waiting {wait}s...", file=sys.stderr)
                import time; time.sleep(wait)
                continue
            if response.status_code != 200:
                print(f"DEBUG - Response body: {response.text}", file=sys.stderr)
            response.raise_for_status()
            return response.json()
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"ERROR calling LLM: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"ERROR response text: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def agentic_loop(question):
    system_prompt = """You are a helpful assistant for the SE Toolkit project.

## Tool selection guide
- Wiki/documentation questions -> read_file("wiki/...")
- Source code questions (framework, architecture, ETL, Dockerfile) -> read_file on source files
- "How many items", "what status code", "what does endpoint return" -> query_api
- Service status, logs -> run_command
- Explore directory structure -> list_files

## Project structure
- Backend source code: backend/app/
- Backend routers: backend/app/routers/
- Backend main file: backend/app/main.py
- Docker config: docker-compose.yml
- Wiki docs: wiki/

## Important instructions
- For "list all router modules" questions: use list_files ONCE on the routers directory, then immediately give the final answer based on the filenames. Do NOT read each file individually.
- Give the final answer as soon as you have enough information. Do not keep calling tools unnecessarily.
- For HTTP request journey questions: read docker-compose.yml and Dockerfile (located at root, not backend/Dockerfile), then give the complete answer. The Dockerfile is at the project root level.
- For top-learners crash questions: query GET /analytics/top-learners?lab=lab-01, then read backend/app/routers/analytics.py. The bug is in the sorted() call where some scores are None (NoneType). Give the final answer immediately after reading the source.

## query_api usage
- For item counts: GET /items/
- For analytics: GET /analytics/completion-rate?lab=LAB_ID
- For top learners: GET /analytics/top-learners?lab=LAB_ID
- Always report the exact status_code from the response

## Answer format
Be precise and concise. For data questions, state the exact number or value.
For code questions, cite the specific file and function.
For bug diagnosis, name the exact error type and buggy line.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    tool_calls_history = []
    max_iterations = 20

    for iteration in range(max_iterations):
        print(f"DEBUG - Iteration {iteration + 1}", file=sys.stderr)
        response = call_llm(messages, tools=TOOLS)
        message = response['choices'][0]['message']

        if 'tool_calls' in message and message['tool_calls']:
            messages.append({
                "role": "assistant",
                "tool_calls": message['tool_calls'],
                "content": (message.get('content') or '')
            })
            for tool_call in message['tool_calls']:
                print(f"DEBUG - Calling tool: {tool_call['function']['name']} args: {tool_call['function']['arguments']}", file=sys.stderr)
                tool_result = execute_tool(tool_call)
                messages.append(tool_result)
                result_preview = tool_result['content']
                if len(result_preview) > 500:
                    result_preview = result_preview[:500] + "..."
                tool_calls_history.append({
                    "tool": tool_call['function']['name'],
                    "args": json.loads(tool_call['function']['arguments']),
                    "result": result_preview
                })
        else:
            answer = (message.get('content') or '')
            source = None
            read_source = None
            api_source = None
            for tc in tool_calls_history:
                if tc['tool'] in ('read_file', 'list_files'):
                    read_source = tc['args'].get('path', 'unknown')
                elif tc['tool'] == 'query_api':
                    api_source = 'api'
                elif tc['tool'] == 'run_command':
                    source = 'system'
            # Prefer read_file source, fall back to api
            if read_source:
                source = read_source
            elif api_source:
                source = api_source
            if source is None:
                source = 'unknown'
            return {'answer': answer, 'source': source, 'tool_calls': tool_calls_history}

    return {'answer': "Maximum tool calls reached without final answer", 'source': 'unknown', 'tool_calls': tool_calls_history}


def main():
    parser = argparse.ArgumentParser(description='System agent with tools')
    parser.add_argument('question', help='Question about the system or documentation')
    args = parser.parse_args()
    print(f"Question: {args.question}", file=sys.stderr)
    result = agentic_loop(args.question)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
