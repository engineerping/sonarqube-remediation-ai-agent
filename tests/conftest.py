# tests/conftest.py
import os
from typing import Dict, Any
import pytest

# Set required env vars before any config.py import occurs
os.environ.setdefault("SONAR_URL", "http://localhost:9000")
os.environ.setdefault("SONAR_TOKEN", "test-token")
os.environ.setdefault("PGVECTOR_DSN", "postgresql://test:test@localhost/test")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_REPO", "test/repo")
os.environ.setdefault("REPO_LOCAL_PATH", "/tmp/test-repo")
os.environ.setdefault("LLM_MODEL", "claude-sonnet-4-6")

from state import AgentState


@pytest.fixture(autouse=True)
def reset_sonarqube_client():
    """Reset singleton clients between tests to prevent state leakage."""
    import agents.issue_reader.tools as issue_reader_tools
    issue_reader_tools._client = None
    try:
        import agents.remediation.tools as remediation_tools
        remediation_tools._retriever = None
    except ImportError:
        pass
    try:
        import agents.validation.tools as validation_tools
        validation_tools._client = None
    except ImportError:
        pass
    yield
    import agents.issue_reader.tools as issue_reader_tools
    issue_reader_tools._client = None
    try:
        import agents.remediation.tools as remediation_tools
        remediation_tools._retriever = None
    except ImportError:
        pass
    try:
        import agents.validation.tools as validation_tools
        validation_tools._client = None
    except ImportError:
        pass


def make_state(**kwargs) -> AgentState:
    defaults: Dict[str, Any] = {
        "project_key": "test:project",
        "branch": "main",
        "issues": [],
        "fixes": [],
        "validation_result": None,
        "round_number": 0,
        "max_rounds": 3,
        "pr_url": None,
        "messages": [],
    }
    defaults.update(kwargs)
    return defaults  # type: ignore
