#!/usr/bin/env python3
"""Test script for all API routes"""

import requests
import sys
from typing import Any, Dict

BASE_URL = "http://127.0.0.1:8080/api/v1"


def print_result(test_name: str, success: bool, response: Any = None, error: str = None):
    """Print test result"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status}: {test_name}")

    if error:
        print(f"  Error: {error}")
    elif response is not None:
        if isinstance(response, dict):
            print(f"  Response keys: {list(response.keys())[:5]}")
        elif isinstance(response, list):
            print(f"  Response length: {len(response)}")
        else:
            print(f"  Response: {str(response)[:100]}")
    print()


def test_health():
    """Test health check endpoint"""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        return resp.status_code == 200, resp.json(), None
    except Exception as e:
        return False, None, str(e)


def test_info_routes():
    """Test all info routes"""
    results = []

    # /info/summary
    try:
        resp = requests.get(f"{BASE_URL}/info/summary", timeout=5)
        results.append(("info/summary", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/summary", False, None, str(e)))

    # /info/routes
    try:
        resp = requests.get(f"{BASE_URL}/info/routes", timeout=5)
        results.append(("info/routes", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/routes", False, None, str(e)))

    # /info/runs
    try:
        resp = requests.get(f"{BASE_URL}/info/runs", timeout=5)
        results.append(("info/runs", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/runs", False, None, str(e)))

    # /info/workflow/current
    try:
        resp = requests.get(f"{BASE_URL}/info/workflow/current", timeout=5)
        results.append(("info/workflow/current", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/workflow/current", False, None, str(e)))

    # /info/workflow/latest
    try:
        resp = requests.get(f"{BASE_URL}/info/workflow/latest", timeout=5)
        results.append(("info/workflow/latest", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/workflow/latest", False, None, str(e)))

    # /info/agent-team
    try:
        resp = requests.get(f"{BASE_URL}/info/agent-team", timeout=5)
        results.append(("info/agent-team", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/agent-team", False, None, str(e)))

    # /info/agent-team?project_id=test
    try:
        resp = requests.get(f"{BASE_URL}/info/agent-team?project_id=test", timeout=5)
        results.append(("info/agent-team (with project_id)", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/agent-team (with project_id)", False, None, str(e)))

    # /info/interactions
    try:
        resp = requests.get(f"{BASE_URL}/info/interactions", timeout=5)
        results.append(("info/interactions", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("info/interactions", False, None, str(e)))

    # /thinking/modes
    try:
        resp = requests.get(f"{BASE_URL}/thinking/modes", timeout=5)
        results.append(("thinking/modes", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("thinking/modes", False, None, str(e)))

    # /thoughts/{session_id}
    try:
        resp = requests.get(f"{BASE_URL}/thoughts/test-session-123", timeout=5)
        results.append(("thoughts/{session_id}", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("thoughts/{session_id}", False, None, str(e)))

    # POST /thinking/config
    try:
        resp = requests.post(f"{BASE_URL}/thinking/config", json={}, timeout=5)
        results.append(("POST thinking/config", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("POST thinking/config", False, None, str(e)))

    return results


def test_agents_routes():
    """Test all agents routes"""
    results = []

    # GET /agents
    try:
        resp = requests.get(f"{BASE_URL}/agents", timeout=5)
        results.append(("GET /agents", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /agents", False, None, str(e)))

    # GET /agents/{agent_id}
    try:
        resp = requests.get(f"{BASE_URL}/agents/wang", timeout=5)
        results.append(("GET /agents/wang", resp.status_code in [200, 404], resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /agents/wang", False, None, str(e)))

    # GET /agents/{agent_id}/status
    try:
        resp = requests.get(f"{BASE_URL}/agents/wang/status", timeout=5)
        results.append(("GET /agents/wang/status", resp.status_code in [200, 404], resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /agents/wang/status", False, None, str(e)))

    return results


def test_chat_routes():
    """Test all chat routes"""
    results = []

    # POST /chat
    try:
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "Hello", "agent_id": "wangyue"},
            timeout=30
        )
        results.append(("POST /chat", resp.status_code in [200, 500], resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("POST /chat", False, None, str(e)))

    # GET /chat/history
    try:
        resp = requests.get(f"{BASE_URL}/chat/history", timeout=5)
        results.append(("GET /chat/history", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /chat/history", False, None, str(e)))

    # GET /chat/sessions
    try:
        resp = requests.get(f"{BASE_URL}/chat/sessions", timeout=5)
        results.append(("GET /chat/sessions", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /chat/sessions", False, None, str(e)))

    return results


def test_memory_routes():
    """Test all memory routes"""
    results = []

    # GET /memory/short-term
    try:
        resp = requests.get(f"{BASE_URL}/memory/short-term?agent_id=wang", timeout=5)
        results.append(("GET /memory/short-term", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /memory/short-term", False, None, str(e)))

    # GET /memory/long-term
    try:
        resp = requests.get(f"{BASE_URL}/memory/long-term?agent_id=wang", timeout=5)
        results.append(("GET /memory/long-term", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /memory/long-term", False, None, str(e)))

    # GET /memory/handover
    try:
        resp = requests.get(f"{BASE_URL}/memory/handover?agent_id=wang", timeout=5)
        results.append(("GET /memory/handover", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /memory/handover", False, None, str(e)))

    # POST /memory/write
    try:
        resp = requests.post(
            f"{BASE_URL}/memory/write",
            json={
                "content": "Test memory content",
                "agent_id": "wang",
                "memory_type": "short_term"
            },
            timeout=5
        )
        results.append(("POST /memory/write", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("POST /memory/write", False, None, str(e)))

    return results


def test_token_usage_routes():
    """Test all token usage routes"""
    results = []

    # GET /token-usage
    try:
        resp = requests.get(f"{BASE_URL}/token-usage", timeout=5)
        results.append(("GET /token-usage", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /token-usage", False, None, str(e)))

    # GET /token-usage/{agent_id}
    try:
        resp = requests.get(f"{BASE_URL}/token-usage/wangyue", timeout=5)
        results.append(("GET /token-usage/wangyue", resp.status_code in [200, 500], resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /token-usage/wangyue", False, None, str(e)))

    # POST /token-usage/{agent_id}/reset
    try:
        resp = requests.post(f"{BASE_URL}/token-usage/wangyue/reset", timeout=5)
        results.append(("POST /token-usage/wangyue/reset", resp.status_code in [200, 500], resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("POST /token-usage/wangyue/reset", False, None, str(e)))

    return results


def test_projects_routes():
    """Test all projects routes"""
    results = []

    # GET /projects
    try:
        resp = requests.get(f"{BASE_URL}/projects", timeout=5)
        results.append(("GET /projects", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /projects", False, None, str(e)))

    # POST /projects - create a test project
    project_id = None
    try:
        resp = requests.post(
            f"{BASE_URL}/projects",
            json={"name": "Test Project", "description": "Test description"},
            timeout=5
        )
        result_data = resp.json() if resp.ok else None
        if resp.ok and result_data:
            project_id = result_data.get("project_id")
        results.append(("POST /projects", resp.status_code in [200, 400], result_data, None))
    except Exception as e:
        results.append(("POST /projects", False, None, str(e)))

    # GET /projects/{project_id}
    if project_id:
        try:
            resp = requests.get(f"{BASE_URL}/projects/{project_id}", timeout=5)
            results.append(("GET /projects/{project_id}", resp.status_code in [200, 404], resp.json() if resp.ok else None, None))
        except Exception as e:
            results.append(("GET /projects/{project_id}", False, None, str(e)))

    # GET /projects/{project_id}/agents
    if project_id:
        try:
            resp = requests.get(f"{BASE_URL}/projects/{project_id}/agents", timeout=5)
            results.append(("GET /projects/{project_id}/agents", resp.status_code == 200, resp.json() if resp.ok else None, None))
        except Exception as e:
            results.append(("GET /projects/{project_id}/agents", False, None, str(e)))

    return results


def test_logs_routes():
    """Test all logs routes"""
    results = []

    # GET /logs
    try:
        resp = requests.get(f"{BASE_URL}/logs?limit=10", timeout=5)
        results.append(("GET /logs", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /logs", False, None, str(e)))

    # GET /logs/stats
    try:
        resp = requests.get(f"{BASE_URL}/logs/stats", timeout=5)
        results.append(("GET /logs/stats", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /logs/stats", False, None, str(e)))

    # GET /logs/files
    try:
        resp = requests.get(f"{BASE_URL}/logs/files", timeout=5)
        results.append(("GET /logs/files", resp.status_code == 200, resp.json() if resp.ok else None, None))
    except Exception as e:
        results.append(("GET /logs/files", False, None, str(e)))

    return results


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing All API Routes")
    print("=" * 60)
    print()

    # Check if server is running
    print("Checking server availability...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        if resp.status_code != 200:
            print(f"✗ Server is not responding correctly. Status: {resp.status_code}")
            print()
            print("Please start the server first:")
            print("  cd /Users/agent/PycharmProjects/mul-agent")
            print("  uvicorn mul_agent.api.server:app --host 0.0.0.0 --port 8000")
            return 1
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server")
        print()
        print("Please start the server first:")
        print("  cd /Users/agent/PycharmProjects/mul-agent")
        print("  uvicorn mul_agent.api.server:app --host 0.0.0.0 --port 8000")
        return 1
    except Exception as e:
        print(f"✗ Error checking server: {e}")
        return 1

    print("✓ Server is running")
    print()

    all_results = []

    # Test each group
    test_groups = [
        ("Health Check", test_health),
        ("Info Routes", test_info_routes),
        ("Agents Routes", test_agents_routes),
        ("Chat Routes", test_chat_routes),
        ("Memory Routes", test_memory_routes),
        ("Token Usage Routes", test_token_usage_routes),
        ("Projects Routes", test_projects_routes),
        ("Logs Routes", test_logs_routes),
    ]

    for group_name, test_func in test_groups:
        print("-" * 60)
        print(f"Testing: {group_name}")
        print("-" * 60)

        result = test_func()

        if isinstance(result, list):
            # Multiple results from this test
            for test_name, success, response, error in result:
                print_result(test_name, success, response, error)
                all_results.append((test_name, success))
        else:
            # Single result
            test_name = test_func.__name__.replace("test_", "")
            success, response, error = result
            print_result(test_name, success, response, error)
            all_results.append((test_name, success))

        print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in all_results if success)
    failed = len(all_results) - passed
    total = len(all_results)

    print(f"Total: {total} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed > 0:
        print("Failed tests:")
        for test_name, success in all_results:
            if not success:
                print(f"  - {test_name}")
        print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
