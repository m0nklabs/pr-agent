"""render_previous_findings: earlier findings must reach the /review prompt.

Ported from upstream qodo-ai/pr-agent. Without this block the model never sees
prior findings, so any dedupe instruction in the prompt is unenforceable.
"""

import json

from pr_agent.algo.review_finding_state import render_previous_findings


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
