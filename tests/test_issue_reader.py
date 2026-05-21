# tests/test_issue_reader.py
from unittest.mock import patch, MagicMock
from agents.issue_reader.agent import issue_reader_node
from tests.conftest import make_state


@patch("agents.issue_reader.tools.SonarQubeClient.get_issues")
@patch("agents.issue_reader.tools.SonarQubeClient.get_rule")
@patch("agents.issue_reader.tools.SonarQubeClient.get_source")
def test_issue_reader_node_maps_api_response(mock_source, mock_rule, mock_issues):
    mock_issues.return_value = [
        {
            "key": "AX123",
            "rule": "java:S1192",
            "component": "test:proj:src/main/java/PaymentService.java",
            "textRange": {"startLine": 10, "endLine": 10},
            "severity": "MAJOR",
            "message": "String literal duplicated",
        }
    ]
    mock_rule.return_value = {
        "key": "java:S1192",
        "name": "String literals should not be duplicated",
        "htmlDesc": "Duplicating a string literal ...",
        "remFnBaseEffort": "5min",
    }
    mock_source.return_value = '        String status = "PENDING";'

    state = make_state()
    result = issue_reader_node(state)

    assert len(result["issues"]) == 1
    issue = result["issues"][0]
    assert issue["issue_key"] == "AX123"
    assert issue["rule_id"] == "java:S1192"
    assert issue["severity"] == "MAJOR"
    assert issue["line_start"] == 10
    assert "PENDING" in issue["code_snippet"]


@patch("agents.issue_reader.tools.SonarQubeClient.get_issues")
def test_issue_reader_returns_empty_when_no_issues(mock_issues):
    mock_issues.return_value = []
    state = make_state()
    result = issue_reader_node(state)
    assert result["issues"] == []
