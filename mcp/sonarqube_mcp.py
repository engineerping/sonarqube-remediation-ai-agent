# mcp/sonarqube_mcp.py
import os
import time
from typing import List, Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


class SonarQubeClient:
    """REST client matching the SonarQube MCP Server tool interface."""

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        self.url = (url or os.environ["SONAR_URL"]).rstrip("/")
        self.token = token or os.environ["SONAR_TOKEN"]
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, path: str, params: dict = None) -> dict:
        resp = self.session.get(f"{self.url}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_issues(self, project_key: str, branch: str,
                   severities: Optional[List[str]] = None) -> List[Dict]:
        params = {
            "projectKeys": project_key,
            "branch": branch,
            "statuses": "OPEN",
            "ps": 500,
        }
        if severities:
            params["severities"] = ",".join(severities)
        data = self._get("/api/issues/search", params)
        return data.get("issues", [])

    def get_rule(self, rule_key: str) -> Dict:
        data = self._get("/api/rules/show", {"key": rule_key})
        return data.get("rule", {})

    def get_source(self, component_key: str,
                   from_line: int, to_line: int) -> str:
        data = self._get("/api/sources/lines", {
            "key": component_key,
            "from": max(1, from_line),
            "to": to_line,
        })
        lines = data.get("sources", [])
        return "\n".join(src.get("code", "") for src in lines)

    def trigger_scan(self, project_key: str, sonar_url: str,
                     repo_path: str) -> str:
        """Run sonar-scanner CLI and return the CE task ID."""
        import subprocess
        result = subprocess.run(
            [
                "sonar-scanner",
                f"-Dsonar.projectKey={project_key}",
                f"-Dsonar.host.url={sonar_url}",
                f"-Dsonar.token={self.token}",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            safe_stderr = result.stderr.replace(self.token, "***")
            raise RuntimeError(f"sonar-scanner failed:\n{safe_stderr}")
        for line in result.stdout.splitlines():
            if "task?id=" in line:
                return line.split("task?id=")[-1].strip()
        raise RuntimeError("Could not extract CE task ID from sonar-scanner output")

    def poll_task(self, task_id: str, timeout: int = 300) -> Dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self._get("/api/ce/task", {"id": task_id})
            task = data.get("task", {})
            status = task.get("status")
            if status == "SUCCESS":
                return task
            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"SonarQube task {task_id} ended with status {status}")
            time.sleep(10)
        raise TimeoutError(f"SonarQube task {task_id} did not complete in {timeout}s")

    def check_issues_resolved(self, project_key: str, branch: str,
                               issue_keys: List[str]) -> Dict:
        """Return which of the given issue keys are still OPEN."""
        all_open = self.get_issues(project_key, branch)
        open_keys = {i["key"] for i in all_open}
        resolved = [k for k in issue_keys if k not in open_keys]
        remaining_raw = [i for i in all_open if i["key"] in issue_keys]
        return {"resolved": resolved, "remaining_raw": remaining_raw}
