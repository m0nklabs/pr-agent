"""Auxiliary auto tools must not prevent the review from running.

The GitHub Action runner executes every enabled tool in one step. Before this
change an exception from /describe aborted the step before /review started,
which was measured on m0nklabs/lastsync#6 (a PR that only touches .gitignore:
pr-agent filters it out, the empty diff made /describe return no prediction and
pr_description raised).
"""

import pytest

from pr_agent.servers.github_action_runner import _run_auto_tool


class _FailingTool:
    def __init__(self, pr_url):
        self.pr_url = pr_url

    async def run(self):
        raise ValueError("no prediction")


class _WorkingTool:
    def __init__(self, pr_url):
        self.pr_url = pr_url

    async def run(self):
        _WorkingTool.ran = True

    ran = False


class _IncompleteTool:
    def __init__(self, pr_url):
        self.pr_url = pr_url

    async def run(self):
        from pr_agent.algo.types import IncompletePullRequestFilesError

        raise IncompletePullRequestFilesError("incomplete")


async def test_fatal_tool_still_fails_the_run():
    with pytest.raises(ValueError):
        await _run_auto_tool(_FailingTool, "url")


async def test_non_fatal_tool_does_not_raise():
    await _run_auto_tool(_FailingTool, "url", fatal=False)


async def test_non_fatal_tool_still_runs_when_healthy():
    _WorkingTool.ran = False
    await _run_auto_tool(_WorkingTool, "url", fatal=False)
    assert _WorkingTool.ran is True


async def test_incomplete_files_error_stays_fatal_even_when_not_fatal():
    """That error publishes its own comment and must still fail the run."""
    with pytest.raises(Exception):
        await _run_auto_tool(_IncompleteTool, "url", fatal=False)
