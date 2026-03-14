#!/usr/bin/env python3
"""
Agent CLI for calling LLM.
Usage: uv run agent.py "Your question here"
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv('.env.agent.secret')

# Configuration - используем OPENROUTER_API_KEY чтобы избежать конфликта
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_BASE = os.getenv('LLM_API_BASE')
LLM_MODEL = os.getenv('LLM_MODEL')

# Debug
print(f"DEBUG - OPENROUTER_API_KEY loaded: {'Yes' if OPENROUTER_API_KEY else 'No'}", file=sys.stderr)
print(f"DEBUG - LLM_API_BASE: {LLM_API_BASE}", file=sys.stderr)
print(f"DEBUG - LLM_MODEL: {LLM_MODEL}", file=sys.stderr)

# Проверки
if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in environment", file=sys.stderr)
    sys.exit(1)

if not LLM_API_BASE:
    print("ERROR: LLM_API_BASE not found in environment", file=sys.stderr)
    sys.exit(1)

if not LLM_MODEL:
    print("ERROR: LLM_MODEL not found in environment", file=sys.stderr)
    sys.exit(1)

def call_llm(question):
    """Call LLM and return response"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENROUTER_API_KEY.strip()}',
        'User-Agent': 'curl/8.5.0',
        'HTTP-Referer': 'https://se-toolkit-lab-6.local',
        'X-Title': 'SE Toolkit Lab 6 Agent'
    }
    
    data = {
        'model': LLM_MODEL,
        'messages': [
            {"role": "user", "content": question}
        ],
        'temperature': 0.7,
        'max_tokens': 1000
    }
    
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

def main():
    parser = argparse.ArgumentParser(description='Call LLM with question')
    parser.add_argument('question', help='Question to ask the LLM')
    args = parser.parse_args()
    
    print(f"Question: {args.question}", file=sys.stderr)
    print(f"Using model: {LLM_MODEL}", file=sys.stderr)
    
    result = call_llm(args.question)
    
    if 'choices' in result and len(result['choices']) > 0:
        answer = result['choices'][0]['message']['content']
    else:
        answer = "No answer received"
    
    output = {
        'answer': answer.strip(),
        'tool_calls': []
    }
    print(json.dumps(output))

if __name__ == '__main__':
    main()

