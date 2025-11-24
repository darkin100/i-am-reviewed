"""GitHub platform implementation using GitHub CLI."""

import os
import json
import subprocess
from typing import Dict, Optional, List

from pr_agent.platforms.base import GitPlatform


class GitHubPlatform(GitPlatform):
    """GitHub platform implementation using gh CLI.

    This implementation uses the GitHub CLI (gh) to interact with GitHub's API.
    """

    def get_pr_info(self, repo: str, pr_number: int) -> Dict:
        """Fetch PR metadata using GitHub CLI.

        Args:
            repo: Repository in format 'owner/repo'
            pr_number: Pull request number

        Returns:
            Dictionary with PR metadata (title, body, author, branches)

        Raises:
            subprocess.CalledProcessError: If the gh command fails
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

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch PR diff using GitHub CLI.

        Args:
            repo: Repository in format 'owner/repo'
            pr_number: Pull request number

        Returns:
            Diff content as string

        Raises:
            subprocess.CalledProcessError: If the gh command fails
        """
        cmd = ['gh', '-R', repo, 'pr', 'diff', str(pr_number)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout

    def post_pr_comment(self, repo: str, pr_number: int, body: str) -> None:
        """Post a comment on the PR using GitHub CLI.

        Args:
            repo: Repository in format 'owner/repo'
            pr_number: Pull request number
            body: Comment text (supports markdown)

        Raises:
            subprocess.CalledProcessError: If the gh command fails
        """
        cmd = ['gh', '-R', repo, 'pr', 'comment', str(pr_number), '--body', body]

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

    def setup_auth(self) -> None:
        """Set up GitHub CLI authentication.

        GitHub CLI authentication is typically handled externally:
        - Locally: via 'gh auth login'

        This method is a no-op as gh CLI handles authentication automatically.
        """
        # No authentication setup needed - gh CLI handles this automatically
        pass

    def validate_environment_variables(self) -> List[str]:
        """Validate GitHub-specific environment variables.

        Checks for repository identifier and PR number, using either:
        - GitHub authentication: GH_TOKEN (required for API access)

        Returns:
            List of missing environment variable names (empty list if all present)
        """
        missing_vars = []

        # Check authentication token
        gh_token = os.getenv('GH_TOKEN')

        if not gh_token:
            missing_vars.append('GH_TOKEN')

        return missing_vars
