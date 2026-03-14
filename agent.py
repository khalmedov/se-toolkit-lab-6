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

# Load environment variables
load_dotenv('.env.agent.secret')

# Configuration
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42011')
LMS_API_KEY = os.getenv('LMS_API_KEY', 'my-secret-api-key')

# Проверка наличия ключа
if not LLM_API_KEY or not LLM_API_BASE or not LLM_MODEL:
    print("ERROR: Missing required environment variables", file=sys.stderr)
    sys.exit(1)

# Security: project root
PROJECT_ROOT = Path(__file__).parent.absolute()

# Tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
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
            "description": "List files and directories at a given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
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
            "description": "Run a system command on the VM (safe commands only)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute (e.g., 'docker ps', 'ls -la', 'df -h')"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
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
            "description": "Query the LMS API endpoint to get data about items, stats, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "API endpoint (e.g., '/items/', '/items/stats?lab=lab-04', '/pipeline/sync')"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST"],
                        "description": "HTTP method",
                        "default": "GET"
                    }
                },
                "required": ["endpoint"]
            }
        }
    }
]

def read_file(path):
    """Read file contents with security check"""
    try:
        # Security: prevent directory traversal
        requested_path = (PROJECT_ROOT / path).resolve()
        if not str(requested_path).startswith(str(PROJECT_ROOT)):
            return "Error: Access denied (path outside project directory)"
        
        if not requested_path.exists():
            return f"Error: File not found: {path}"
        
        if not requested_path.is_file():
            return f"Error: Not a file: {path}"
        
        return requested_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path):
    """List directory contents with security check"""
    try:
        # Security: prevent directory traversal
        requested_path = (PROJECT_ROOT / path).resolve()
        if not str(requested_path).startswith(str(PROJECT_ROOT)):
            return "Error: Access denied (path outside project directory)"
        
        if not requested_path.exists():
            return f"Error: Path not found: {path}"
        
        if not requested_path.is_dir():
            return f"Error: Not a directory: {path}"
        
        items = []
        for item in requested_path.iterdir():
            items.append(f"{'📁' if item.is_dir() else '📄'} {item.name}")
        
        return "\n".join(items)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def run_command(command, timeout=10):
    """Execute system command with security checks"""
    
    # Security: список запрещенных команд/паттернов
    forbidden_patterns = [
        'rm -rf', 'sudo', 'dd', 'mkfs', 'format', 
        '>', '>>', '|', ';', '&&', '||',
        'chmod', 'chown', 'kill', 'pkill',
        'reboot', 'shutdown', 'init', 'systemctl'
    ]
    
    command_lower = command.lower()
    for pattern in forbidden_patterns:
        if pattern in command_lower:
            return f"Error: Command contains forbidden pattern '{pattern}'. This command is blocked for security reasons."
    
    try:
        # Разбиваем команду безопасно
        args = shlex.split(command)
        
        # Выполняем с таймаутом
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        output = f"Exit code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        
        if result.returncode != 0:
            output += f"Command failed with exit code {result.returncode}"
        
        return output
        
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return f"Error: Command not found: '{command}'. The command may not be installed or available in PATH."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def query_api(endpoint, method="GET"):
    """Query the LMS API endpoint"""
    headers = {
        'Authorization': f'Bearer {LMS_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    url = f"{AGENT_API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        else:  # POST
            response = requests.post(url, headers=headers, timeout=10)
            
        response.raise_for_status()
        
        # Pretty print JSON if possible
        try:
            data = response.json()
            return json.dumps(data, indent=2, ensure_ascii=False)
        except:
            return response.text
            
    except requests.exceptions.RequestException as e:
        return f"Error querying API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def execute_tool(tool_call):
    """Execute a tool and return result"""
    tool_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])
    
    if tool_name == 'read_file':
        result = read_file(args['path'])
    elif tool_name == 'list_files':
        result = list_files(args['path'])
    elif tool_name == 'run_command':
        result = run_command(args['command'], args.get('timeout', 10))
    elif tool_name == 'query_api':
        result = query_api(args['endpoint'], args.get('method', 'GET'))
    else:
        result = f"Error: Unknown tool {tool_name}"
    
    return {
        "role": "tool",
        "tool_call_id": tool_call['id'],
        "name": tool_name,
        "content": result
    }

def call_llm(messages, tools=None):
    """Call LLM with messages and tools"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LLM_API_KEY.strip()}'
    }
    
    data = {
        'model': LLM_MODEL,
        'messages': messages
    }
    
    if tools:
        data['tools'] = tools
        data['tool_choice'] = 'auto'
    
    print(f"\n🔍 DEBUG - Request URL: {LLM_API_BASE}/chat/completions", file=sys.stderr)
    
    try:
        response = requests.post(
            f"{LLM_API_BASE}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        print(f"📡 Response status: {response.status_code}", file=sys.stderr)
        
        if response.status_code != 200:
            print(f"📡 Response body: {response.text}", file=sys.stderr)
            
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"❌ Error calling LLM: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"❌ Response text: {e.response.text}", file=sys.stderr)
        sys.exit(1)

def agentic_loop(question):
    """Run the agentic loop"""
    system_prompt = """You are a system administrator assistant for the SE Toolkit project.
You have access to tools that help you understand and manage the system.

Available tools:
- list_files(path): list directory contents
- read_file(path): read a file
- run_command(command, timeout): execute safe system commands
- query_api(endpoint, method): query the LMS API for data

Guidelines for run_command:
1. Use it to check service status (docker ps, systemctl status)
2. View logs (docker logs, journalctl)
3. Monitor system (ps aux, df -h, free -m)
4. NEVER use destructive commands (rm, sudo, dd, etc.) - they are blocked

Guidelines for query_api:
1. Use it to get data about items, stats, etc.
2. Common endpoints: /items/, /items/stats?lab=lab-04, /pipeline/sync
3. Use GET for reading data, POST for actions

Always explain what you're doing and why.
Include command output in your reasoning.
If a command fails, suggest alternatives.
For documentation questions, use read_file and list_files.
For system questions, use run_command.
For API data, use query_api.

Format source as:
- For docs: wiki/filename.md#section
- For system: "system" or command name
- For API: "api"
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    max_iterations = 15
    
    for iteration in range(max_iterations):
        print(f"DEBUG - Iteration {iteration + 1}", file=sys.stderr)
        
        response = call_llm(messages, tools=TOOLS)
        message = response['choices'][0]['message']
        
        # Check if there are tool calls
        if 'tool_calls' in message and message['tool_calls']:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "tool_calls": message['tool_calls'],
                "content": message.get('content', '')
            })
            
            # Execute each tool call
            for tool_call in message['tool_calls']:
                tool_result = execute_tool(tool_call)
                messages.append(tool_result)
                
                # Record for output (truncate long results)
                result_preview = tool_result['content']
                if len(result_preview) > 300:
                    result_preview = result_preview[:300] + "..."
                
                tool_calls_history.append({
                    "tool": tool_call['function']['name'],
                    "args": json.loads(tool_call['function']['arguments']),
                    "result": result_preview
                })
        else:
            # No tool calls - final answer
            answer = message.get('content', '')
            
            # Try to extract source from answer
            source = "unknown"
            lines = answer.split('\n')
            for line in lines:
                if 'wiki/' in line and '.md' in line:
                    words = line.split()
                    for word in words:
                        if word.startswith('wiki/') and '.md' in word:
                            source = word.strip('.,;:')
                            break
                elif 'docker' in line.lower() or 'command' in line.lower():
                    source = "system"
                elif 'api' in line.lower() or 'endpoint' in line.lower():
                    source = "api"
            
            return {
                'answer': answer,
                'source': source,
                'tool_calls': tool_calls_history
            }
    
    # Max iterations reached
    return {
        'answer': "Maximum tool calls reached without final answer",
        'source': "unknown",
        'tool_calls': tool_calls_history
    }

def main():
    parser = argparse.ArgumentParser(description='System administrator agent with tools')
    parser.add_argument('question', help='Question about the system or documentation')
    args = parser.parse_args()
    
    print(f"Question: {args.question}", file=sys.stderr)
    
    result = agentic_loop(args.question)
    
    # Output JSON to stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
