"""GitHub CLI wrapper functions for PR operations."""

import subprocess
import json
from typing import Dict


def get_pr_info(repo: str, pr_number: int) -> Dict:
    """
    Get PR metadata using GitHub CLI.

    Args:
        repo: Repository in format 'owner/repo'
        pr_number: Pull request number

    Returns:
        Dictionary with PR metadata (title, body, author, branches)
    """
    cmd = [
        'gh', '-R', repo, 'pr', 'view', str(pr_number),
        '--json', 'title,body,author,headRefName,baseRefName'
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    return json.loads(result.stdout)


def get_pr_diff(repo: str, pr_number: int) -> str:
    """
    Get PR diff using GitHub CLI.

    Args:
        repo: Repository in format 'owner/repo'
        pr_number: Pull request number

    Returns:
        Diff content as string
    """
    cmd = ['gh', '-R', repo, 'pr', 'diff', str(pr_number)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout


def post_pr_comment(repo: str, pr_number: int, body: str) -> None:
    """
    Post a comment on the PR using GitHub CLI.

    Args:
        repo: Repository in format 'owner/repo'
        pr_number: Pull request number
        body: Comment text (supports markdown)
    """
    cmd = ['gh', '-R', repo, 'pr', 'comment', str(pr_number), '--body', body]

    subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )
