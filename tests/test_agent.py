import subprocess
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_agent_basic():
    """Test that agent.py runs and returns valid JSON with answer and tool_calls"""
    
    # Run agent with a simple question
    result = subprocess.run(
        ['uv', 'run', 'agent.py', 'What is 2+2?'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    # Parse JSON from stdout
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"Invalid JSON output: {e}\nStdout: {result.stdout}"
    
    # Check required fields
    assert 'answer' in output, "Missing 'answer' field"
    assert 'tool_calls' in output, "Missing 'tool_calls' field"
    assert isinstance(output['tool_calls'], list), "'tool_calls' should be a list"
    assert len(output['tool_calls']) == 0, "'tool_calls' should be empty for Task 1"
    
    # Check that answer is not empty
    assert output['answer'], "Answer should not be empty"
    
    print("✅ Test passed!")
    
if __name__ == '__main__':
    test_agent_basic()
