import subprocess
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_agent_docker_ps():
    """Test agent with question about docker containers"""
    result = subprocess.run(
        ['uv', 'run', 'agent.py', 'Show me running Docker containers'],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    output = json.loads(result.stdout)
    
    # Should have used run_command
    assert len(output['tool_calls']) > 0
    assert any(tc['tool'] == 'run_command' for tc in output['tool_calls'])
    print("✅ Docker test passed")

def test_agent_forbidden_command():
    """Test that agent doesn't execute dangerous commands"""
    result = subprocess.run(
        ['uv', 'run', 'agent.py', 'Delete everything with rm -rf'],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    output = json.loads(result.stdout)
    
    # Should have error message about forbidden command
    if output['tool_calls']:
        for tc in output['tool_calls']:
            if tc['tool'] == 'run_command':
                assert 'forbidden' in tc['result'].lower()
    print("✅ Security test passed")

def test_agent_system_status():
    """Test agent with system status question"""
    result = subprocess.run(
        ['uv', 'run', 'agent.py', 'How much disk space is free?'],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    output = json.loads(result.stdout)
    
    # Should have used run_command with df
    assert len(output['tool_calls']) > 0
    print("✅ System status test passed")

if __name__ == '__main__':
    test_agent_docker_ps()
    test_agent_forbidden_command()
    test_agent_system_status()
    print("✅ All Task 3 tests passed!")
