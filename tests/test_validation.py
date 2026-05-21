# tests/test_validation.py
from unittest.mock import patch, MagicMock
from agents.validation.agent import validation_node
from state import Issue, Fix, ValidationResult
from tests.conftest import make_state


def make_fix(**kwargs) -> Fix:
    defaults = Fix(
        issue_key="AX123",
        file_path="src/main/java/PaymentService.java",
        unified_diff="--- a/PaymentService.java\n+++ b/PaymentService.java\n",
        original_snippet='String s = "PENDING";',
        fixed_snippet="String s = PENDING_STATUS;",
    )
    defaults.update(kwargs)
    return defaults


def make_issue(**kwargs) -> Issue:
    defaults = Issue(
        issue_key="AX123", rule_id="java:S1192",
        rule_description="", remediation_guidance="",
        severity="MAJOR", file_path="src/main/java/PaymentService.java",
        line_start=5, line_end=5, code_snippet="",
    )
    defaults.update(kwargs)
    return defaults


@patch("agents.validation.tools.SonarQubeClient.trigger_scan")
@patch("agents.validation.tools.SonarQubeClient.poll_task")
@patch("agents.validation.tools.SonarQubeClient.check_issues_resolved")
def test_validation_node_all_resolved(mock_check, mock_poll, mock_scan):
    mock_scan.return_value = "task-id-123"
    mock_poll.return_value = {"status": "SUCCESS", "id": "task-id-123"}
    mock_check.return_value = {
        "resolved": ["AX123"],
        "remaining_raw": [],
    }
    issue = make_issue()
    state = make_state(issues=[issue], fixes=[make_fix()], round_number=1)
    result = validation_node(state)

    vr = result["validation_result"]
    assert vr["all_resolved"] is True
    assert vr["resolved_issues"] == ["AX123"]
    assert vr["remaining_issues"] == []
    assert vr["round_number"] == 1


@patch("agents.validation.tools.SonarQubeClient.trigger_scan")
@patch("agents.validation.tools.SonarQubeClient.poll_task")
@patch("agents.validation.tools.SonarQubeClient.check_issues_resolved")
def test_validation_node_remaining_issues(mock_check, mock_poll, mock_scan):
    mock_scan.return_value = "task-id-456"
    mock_poll.return_value = {"status": "SUCCESS"}
    remaining = make_issue(issue_key="AX123")
    mock_check.return_value = {
        "resolved": [],
        "remaining_raw": [{"key": "AX123"}],
    }
    state = make_state(issues=[remaining], fixes=[make_fix()], round_number=1)
    result = validation_node(state)

    vr = result["validation_result"]
    assert vr["all_resolved"] is False
    assert len(vr["remaining_issues"]) == 1
    assert vr["remaining_issues"][0]["issue_key"] == "AX123"
