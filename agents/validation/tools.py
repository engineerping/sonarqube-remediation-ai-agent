# agents/validation/tools.py
from typing import List, Dict
from mcp.sonarqube_mcp import SonarQubeClient
from config import SONAR_URL, REPO_LOCAL_PATH

_client = None


def get_client() -> SonarQubeClient:
    global _client
    if _client is None:
        _client = SonarQubeClient()
    return _client


def run_scan(project_key: str) -> str:
    return get_client().trigger_scan(project_key, SONAR_URL, REPO_LOCAL_PATH)


def wait_for_scan(task_id: str) -> Dict:
    return get_client().poll_task(task_id)


def check_resolved(project_key: str, branch: str, issue_keys: List[str]) -> Dict:
    return get_client().check_issues_resolved(project_key, branch, issue_keys)
