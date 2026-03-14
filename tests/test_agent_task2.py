import subprocess
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_agent_merge_conflict():
    """Test agent with question about merge conflict"""
    result = subprocess.run(
        ['uv', 'run', 'agent.py', 'How do you resolve a merge conflict?'],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    output = json.loads(result.stdout)
    
    # Check required fields
    assert 'answer' in output
    assert 'source' in output
    assert 'tool_calls' in output
    
    # Should have used read_file
    assert len(output['tool_calls']) > 0
    print(f"✅ Test 1 passed: {len(output['tool_calls'])} tool calls made")

def test_agent_list_files():
    """Test agent with question about wiki files"""
    result = subprocess.run(
        ['uv', 'run', 'agent.py', 'What files are in the wiki?'],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    output = json.loads(result.stdout)
    
    # Should have used list_files
    assert len(output['tool_calls']) > 0
    print(f"✅ Test 2 passed: {len(output['tool_calls'])} tool calls made")

if __name__ == '__main__':
    test_agent_merge_conflict()
    test_agent_list_files()
    print("✅ All Task 2 tests passed!")
