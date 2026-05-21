# agents/issue_reader/tools.py
from typing import List, Dict, Optional
from mcp.sonarqube_mcp import SonarQubeClient

_client: Optional[SonarQubeClient] = None


def get_client() -> SonarQubeClient:
    global _client
    if _client is None:
        _client = SonarQubeClient()
    return _client


def fetch_raw_issues(project_key: str, branch: str) -> List[Dict]:
    return get_client().get_issues(project_key, branch)


def fetch_rule_details(rule_key: str) -> Dict:
    return get_client().get_rule(rule_key)


def fetch_source_snippet(component_key: str, line: int, context: int = 3) -> str:
    return get_client().get_source(
        component_key,
        from_line=max(1, line - context),
        to_line=line + context,
    )
