"""Regression tests for Task 3: System Agent tools."""
import json
import subprocess
import sys


def run_agent(question: str) -> dict:
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"Agent failed: {result.stderr[:300]}"
    return json.loads(result.stdout)


def test_framework_uses_read_file():
    """Question about framework should use read_file tool."""
    data = run_agent("What Python web framework does this project's backend use?")
    assert "answer" in data
    tools_used = [tc["tool"] for tc in data.get("tool_calls", [])]
    assert "read_file" in tools_used, f"Expected read_file, got: {tools_used}"
    assert "fastapi" in data["answer"].lower()


def test_item_count_uses_query_api():
    """Question about item count should use query_api tool."""
    data = run_agent("How many items are currently stored in the database?")
    assert "answer" in data
    tools_used = [tc["tool"] for tc in data.get("tool_calls", [])]
    assert "query_api" in tools_used, f"Expected query_api, got: {tools_used}"
