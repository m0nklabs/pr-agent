"""render_previous_findings: earlier findings must reach the /review prompt.

Ported from upstream qodo-ai/pr-agent. Without this block the model never sees
prior findings, so any dedupe instruction in the prompt is unenforceable.
"""

import json

from pr_agent.algo.review_finding_state import (
    newest_pr_piet_findings_state,
    parse_pr_piet_findings_state,
    render_previous_findings,
)


def _state():
    return {"findings": [
        {"finding_id": "a1", "state": "ACTIVE", "path": "pkg/mod.py",
         "line_start": 10, "line_end": 12,
         "body": "**[verified-bug] Null deref**\n\nCalling .get() on None raises.",
         "last_seen": "2026-11-01T10:00:00Z"},
        {"finding_id": "b2", "state": "RESOLVED", "path": "pkg/other.py",
         "line_start": 3, "line_end": 3,
         "body": "**[backlog] Rename helper**\n\nName is misleading.",
         "resolved_at": "2026-11-01T11:00:00Z"},
    ]}


def test_splits_header_and_content_back_out():
    entries = json.loads(render_previous_findings(_state(), 8000))
    assert entries[0]["issue_header"] == "[verified-bug] Null deref"
    assert entries[0]["issue_content"] == "Calling .get() on None raises."


def test_active_findings_come_before_resolved():
    entries = json.loads(render_previous_findings(_state(), 8000))
    assert [entry["state"] for entry in entries] == ["active", "resolved"]


def test_disabled_and_empty_cases_return_empty_string():
    assert render_previous_findings(_state(), 0) == ""
    assert render_previous_findings(None, 8000) == ""
    assert render_previous_findings({"findings": []}, 8000) == ""


def test_budget_drops_entries_that_do_not_fit():
    assert render_previous_findings(_state(), 120) == ""
    assert len(json.loads(render_previous_findings(_state(), 8000))) == 2


def _marker(entries):
    import json as _json
    payload = _json.dumps({"findings": entries}, separators=(",", ":"))
    return f"<!-- pr-piet-findings:v1 {payload} -->"


def test_parses_pr_piet_review_body_marker():
    body = "## review\n\nfindings text\n\n" + _marker([{
        "id": "pkg/a.py::[verified-bug] X", "state": "active", "path": "pkg/a.py",
        "start_line": 5, "end_line": 7, "header": "[verified-bug] X", "content": "boom",
    }])
    state = parse_pr_piet_findings_state(body)
    assert state is not None
    entry = state["findings"][0]
    assert entry["state"] == "ACTIVE"
    assert entry["finding_id"] == "pkg/a.py::[verified-bug] X"
    # The renderer splits the skeleton body back into header and content.
    rendered = json.loads(render_previous_findings(state, 8000))
    assert rendered[0]["issue_header"] == "[verified-bug] X"
    assert rendered[0]["issue_content"] == "boom"


def test_newest_state_wins_when_several_reviews_carry_one():
    older = _marker([{"id": "a", "state": "active", "path": "a.py", "header": "old", "content": "c"}])
    newer = _marker([{"id": "b", "state": "active", "path": "b.py", "header": "new", "content": "c"}])
    state = newest_pr_piet_findings_state(["no marker", older, "also none", newer])
    assert [finding["finding_id"] for finding in state["findings"]] == ["b"]


def test_missing_or_malformed_marker_yields_none():
    assert newest_pr_piet_findings_state(["plain", ""]) is None
    assert parse_pr_piet_findings_state("<!-- pr-piet-findings:v1 {not json} -->") is None
    assert parse_pr_piet_findings_state(_marker([])) is None
