#!/usr/bin/env python3
"""
Agent CLI for calling LLM with tools.
Usage: uv run agent.py "Your question here"
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
import argparse
from pathlib import Path

# Load environment variables
load_dotenv('.env.agent.secret')

# Configuration
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL')

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

def execute_tool(tool_call):
    """Execute a tool and return result"""
    tool_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])
    
    if tool_name == 'read_file':
        result = read_file(args['path'])
    elif tool_name == 'list_files':
        result = list_files(args['path'])
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
        'Authorization': f'Bearer {LLM_API_KEY.strip()}',
        'User-Agent': 'curl/8.5.0',
        'HTTP-Referer': 'https://se-toolkit-lab-6.local',
        'X-Title': 'SE Toolkit Lab 6 Agent'
    }
    
    data = {
        'model': LLM_MODEL,
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 2000
    }
    
    if tools:
        data['tools'] = tools
        data['tool_choice'] = 'auto'
    
    try:
        response = requests.post(
            f"{LLM_API_BASE}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

def agentic_loop(question):
    """Run the agentic loop"""
    system_prompt = """You are a documentation assistant for the SE Toolkit project.
Use the available tools to help users find information.

Rules:
1. First, use list_files to explore the wiki directory
2. Then use read_file to read relevant files
3. Always include the source in your final answer (file path and section if applicable)
4. Format source as: wiki/filename.md#section

Available tools:
- read_file(path): read a file
- list_files(path): list directory contents"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    max_iterations = 10
    
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
                
                # Record for output
                tool_calls_history.append({
                    "tool": tool_call['function']['name'],
                    "args": json.loads(tool_call['function']['arguments']),
                    "result": tool_result['content'][:200] + "..." if len(tool_result['content']) > 200 else tool_result['content']
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
    parser = argparse.ArgumentParser(description='Documentation agent with tools')
    parser.add_argument('question', help='Question about the project documentation')
    args = parser.parse_args()
    
    print(f"Question: {args.question}", file=sys.stderr)
    
    result = agentic_loop(args.question)
    
    # Output JSON to stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
