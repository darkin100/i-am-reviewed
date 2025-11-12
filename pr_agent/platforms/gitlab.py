"""GitLab platform implementation using GitLab CLI."""

import os
import json
import subprocess
from typing import Dict, Optional

from pr_agent.platforms.base import GitPlatform


class GitLabPlatform(GitPlatform):
    """GitLab platform implementation using glab CLI.

    This implementation uses the GitLab CLI (glab) to interact with GitLab's API.
    In GitLab CI/CD, authentication is automatically handled via CI_JOB_TOKEN.
    For local development, use: glab auth login
    """

    def get_pr_info(self, repo: str, pr_number: int) -> Dict:
        """Fetch MR metadata using GitLab CLI.

        Args:
            repo: Repository in format 'group/project'
            pr_number: Merge request IID (internal ID)

        Returns:
            Dictionary with MR metadata normalized to match GitHub format:
            - title: MR title
            - body: MR description
            - author: Author info with 'login' key (username)
            - headRefName: Source branch name
            - baseRefName: Target branch name

        Raises:
            subprocess.CalledProcessError: If the glab command fails
        """
        cmd = [
            'glab', 'mr', 'view', str(pr_number),
            '-R', repo,
            '--json'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse GitLab MR data and normalize to GitHub-compatible format
        mr_data = json.loads(result.stdout)

        # Normalize the structure to match GitHub's format
        return {
            'title': mr_data.get('title', ''),
            'body': mr_data.get('description', ''),
            'author': {
                'login': mr_data.get('author', {}).get('username', '')
            },
            'headRefName': mr_data.get('source_branch', ''),
            'baseRefName': mr_data.get('target_branch', '')
        }

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch MR diff using GitLab CLI.

        Args:
            repo: Repository in format 'group/project'
            pr_number: Merge request IID

        Returns:
            Diff content as string

        Raises:
            subprocess.CalledProcessError: If the glab command fails
        """
        cmd = [
            'glab', 'mr', 'diff', str(pr_number),
            '-R', repo
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout

    def post_pr_comment(self, repo: str, pr_number: int, body: str) -> None:
        """Post a comment on the MR using GitLab CLI.

        Args:
            repo: Repository in format 'group/project'
            pr_number: Merge request IID
            body: Comment text (supports markdown)

        Raises:
            subprocess.CalledProcessError: If the glab command fails
        """
        cmd = [
            'glab', 'mr', 'note', str(pr_number),
            '-R', repo,
            '--message', body
        ]

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

    def get_pr_number_from_event(self) -> Optional[int]:
        """Extract MR number from GitLab CI environment context.

        In GitLab CI/CD pipelines, the merge request IID is available in the
        CI_MERGE_REQUEST_IID environment variable.

        Returns:
            MR IID if running in GitLab CI with an MR pipeline, None otherwise
        """
        mr_iid = os.getenv('CI_MERGE_REQUEST_IID')
        if mr_iid:
            try:
                return int(mr_iid)
            except ValueError:
                print(f"Warning: CI_MERGE_REQUEST_IID is not a valid integer: {mr_iid}")
                return None

        return None
