# tests/test_supervisor.py
from orchestrator.supervisor import route
from tests.conftest import make_state
from state import Issue, Fix, ValidationResult


def _issue() -> Issue:
    return Issue(
        issue_key="AX1", rule_id="java:S1192",
        rule_description="", remediation_guidance="",
        severity="MAJOR", file_path="Foo.java",
        line_start=1, line_end=1, code_snippet="",
    )


def _fix() -> Fix:
    return Fix(
        issue_key="AX1", file_path="Foo.java",
        unified_diff="---\n+++\n", original_snippet="", fixed_snippet="",
    )


def test_route_to_issue_reader_when_no_issues():
    assert route(make_state()) == "issue_reader"


def test_route_to_remediator_when_issues_no_fixes():
    assert route(make_state(issues=[_issue()])) == "remediator"


def test_route_to_validator_when_fixes_no_validation():
    assert route(make_state(issues=[_issue()], fixes=[_fix()])) == "validator"


def test_route_to_remediator_when_remaining_issues_and_rounds_left():
    vr = ValidationResult(
        resolved_issues=[], remaining_issues=[_issue()],
        all_resolved=False, round_number=1,
    )
    state = make_state(issues=[_issue()], fixes=[_fix()],
                       validation_result=vr, round_number=1, max_rounds=3)
    assert route(state) == "remediator"


def test_route_to_github_when_all_resolved():
    vr = ValidationResult(
        resolved_issues=["AX1"], remaining_issues=[],
        all_resolved=True, round_number=1,
    )
    state = make_state(issues=[_issue()], fixes=[_fix()],
                       validation_result=vr, round_number=1)
    assert route(state) == "github_agent"


def test_route_to_github_when_max_rounds_reached():
    vr = ValidationResult(
        resolved_issues=[], remaining_issues=[_issue()],
        all_resolved=False, round_number=3,
    )
    state = make_state(issues=[_issue()], fixes=[_fix()],
                       validation_result=vr, round_number=3, max_rounds=3)
    assert route(state) == "github_agent"
