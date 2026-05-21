# tests/conftest.py
import os
from typing import Dict, Any

# Set required env vars before any config.py import occurs
os.environ.setdefault("SONAR_URL", "http://localhost:9000")
os.environ.setdefault("SONAR_TOKEN", "test-token")
os.environ.setdefault("PGVECTOR_DSN", "postgresql://test:test@localhost/test")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_REPO", "test/repo")
os.environ.setdefault("REPO_LOCAL_PATH", "/tmp/test-repo")
os.environ.setdefault("LLM_MODEL", "claude-sonnet-4-6")

from state import AgentState


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
