# agents/github/tools.py
import os
import subprocess
from datetime import datetime
from typing import List
from github import Github
from config import GITHUB_TOKEN, GITHUB_REPO, REPO_LOCAL_PATH


def git(cmd: List[str]) -> str:
    result = subprocess.run(
        ["git"] + cmd,
        cwd=REPO_LOCAL_PATH,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def create_branch(project_key: str) -> str:
    safe_key = project_key.replace(":", "-").replace("/", "-")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch_name = f"fix/sonarqube-{safe_key}-{timestamp}"
    git(["checkout", "-b", branch_name])
    return branch_name


def commit_files(file_paths: List[str], rule_id: str, description: str) -> None:
    for fp in file_paths:
        git(["add", fp])
    short_desc = description[:72] if len(description) > 72 else description
    git(["commit", "-m", f"fix({rule_id}): {short_desc}"])


def push_branch(branch_name: str) -> None:
    git(["push", "--set-upstream", "origin", branch_name])


def create_pr(branch_name: str, base_branch: str, pr_body: str,
              n_fixed: int, n_rounds: int) -> str:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    pr = repo.create_pull(
        title=f"fix: auto-remediate {n_fixed} SonarQube issues ({n_rounds} round(s))",
        body=pr_body,
        head=branch_name,
        base=base_branch,
    )
    return pr.html_url
