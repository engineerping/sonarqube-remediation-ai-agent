# tests/test_remediation.py
from unittest.mock import patch, MagicMock, mock_open
from agents.remediation.agent import remediation_node
from state import Issue
from tests.conftest import make_state


def make_issue(**kwargs) -> Issue:
    defaults = Issue(
        issue_key="AX123",
        rule_id="java:S1192",
        rule_description="String literals should not be duplicated",
        remediation_guidance="Extract into a constant",
        severity="MAJOR",
        file_path="src/main/java/PaymentService.java",
        line_start=3,
        line_end=4,
        code_snippet='        String s1 = "PENDING";\n        String s2 = "PENDING";',
    )
    defaults.update(kwargs)
    return defaults


@patch("agents.remediation.tools.RAGRetriever")
@patch("agents.remediation.tools.call_llm")
@patch("agents.remediation.tools.read_file")
@patch("agents.remediation.tools.write_file")
def test_remediation_node_produces_fix(mock_write, mock_read, mock_llm, mock_rag_cls):
    mock_rag = MagicMock()
    mock_rag_cls.return_value = mock_rag
    mock_rag.search.return_value = [
        {"rule_key": "java:S1192", "description": "No duplicate strings", "remediation": "Use constants"}
    ]
    mock_llm.return_value = (
        'private static final String PENDING_STATUS = "PENDING";\n'
        "        String s1 = PENDING_STATUS;\n"
        "        String s2 = PENDING_STATUS;"
    )
    file_content = (
        "public class PaymentService {\n"
        "    public void pay() {\n"
        '        String s1 = "PENDING";\n'
        '        String s2 = "PENDING";\n'
        "    }\n"
        "}"
    )
    mock_read.return_value = file_content

    issue = make_issue()
    state = make_state(issues=[issue])
    result = remediation_node(state)

    assert len(result["fixes"]) == 1
    fix = result["fixes"][0]
    assert fix["issue_key"] == "AX123"
    assert "PENDING_STATUS" in fix["fixed_snippet"]
    assert fix["unified_diff"] != ""
    assert result["validation_result"] is None
    assert result["round_number"] == 1


@patch("agents.remediation.tools.RAGRetriever")
@patch("agents.remediation.tools.call_llm")
@patch("agents.remediation.tools.read_file")
@patch("agents.remediation.tools.write_file")
def test_remediation_node_uses_remaining_issues_on_retry(mock_write, mock_read, mock_llm, mock_rag_cls):
    mock_rag = MagicMock()
    mock_rag_cls.return_value = mock_rag
    mock_rag.search.return_value = []
    mock_llm.return_value = "        String s1 = FIXED;"
    mock_read.return_value = 'public class Foo {\n        String s1 = "dup";\n}'

    remaining_issue = make_issue(issue_key="AX999")
    from state import ValidationResult, Fix
    vr = ValidationResult(
        resolved_issues=["AX123"],
        remaining_issues=[remaining_issue],
        all_resolved=False,
        round_number=1,
    )
    state = make_state(
        issues=[make_issue(), remaining_issue],
        fixes=[Fix(issue_key="AX123", file_path="Foo.java",
                   unified_diff="---\n+++\n", original_snippet="", fixed_snippet="")],
        validation_result=vr,
        round_number=1,
    )
    result = remediation_node(state)

    # Should only fix the remaining issue, not all issues
    assert len(result["fixes"]) == 1
    assert result["fixes"][0]["issue_key"] == "AX999"
    assert result["round_number"] == 2
    assert result["validation_result"] is None
