"""GitHub platform implementation using GitHub CLI."""

import json
import os
import re
import subprocess
from typing import Dict, List, Optional

from agent.logging_config import get_logger
from agent.platforms.base import GitPlatform
from agent.tracing_config import traced

logger = get_logger(__name__)


class GitHubPlatform(GitPlatform):
    """GitHub platform implementation using gh CLI.

    This implementation uses the GitHub CLI (gh) to interact with GitHub's API.
    """

    def __init__(self):
        """Initialize GitHub platform with authentication state."""
        super().__init__()
        self._gh_token: Optional[str] = None
        self._auth_method: Optional[str] = None

    def _get_subprocess_env(self) -> Dict[str, str]:
        """Get environment dict for subprocess calls.

        Returns environment variables to pass to subprocess, including GH_TOKEN
        when using token-based authentication.

        Returns:
            Dictionary of environment variables
        """
        # Start with current environment
        env = os.environ.copy()
        env['NO_COLOR'] = '1'
        env['CLICOLOR'] = '0'

        # Add GH_TOKEN if using token-based auth
        if self._auth_method == 'token' and self._gh_token:
            env['GH_TOKEN'] = self._gh_token

        return env

    @traced("github.get_pr_info")
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
            check=True,
            env=self._get_subprocess_env()
        )

        # Strip ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_output = ansi_escape.sub('', result.stdout)

        pr_data = json.loads(clean_output)
        logger.debug("PR metadata response", extra={"context": {"metadata": pr_data}})

        return pr_data

    @traced("github.get_pr_diff")
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
            check=True,
            env=self._get_subprocess_env()
        )

        return result.stdout

    @traced("github.post_pr_comment")
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
            check=True,
            env=self._get_subprocess_env()
        )

    def setup_auth(self) -> None:
        """Set up GitHub CLI authentication.

        Supports two authentication methods:
        - CI/CD: Uses GH_TOKEN environment variable if available
        - Local: Falls back to gh CLI's local authentication (via 'gh auth login')

        Raises:
            RuntimeError: If neither authentication method is available
        """
        # Check if GH_TOKEN is available (CI mode)
        gh_token = os.getenv('GH_TOKEN')

        if gh_token:
            self._gh_token = gh_token
            self._auth_method = 'token'
            logger.info("GitHub authentication configured", extra={"context": {"method": "GH_TOKEN", "mode": "CI"}})
            return

        # Check if gh CLI is authenticated (local mode)
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True,
                check=False
            )

            # gh auth status returns 0 if authenticated
            if result.returncode == 0:
                self._auth_method = 'cli'
                logger.info("GitHub authentication configured", extra={"context": {"method": "gh_cli", "mode": "interactive"}})
                return
        except FileNotFoundError:
            raise RuntimeError(
                "GitHub CLI (gh) is not installed. "
                "Please install it from https://cli.github.com/"
            )

        # Neither authentication method available
        raise RuntimeError(
            "No GitHub authentication available. Please either:\n"
            "  - Set GH_TOKEN environment variable (for CI/CD), or\n"
            "  - Run 'gh auth login' (for local development)"
        )

    def validate_environment_variables(self) -> List[str]:
        """Validate GitHub-specific environment variables.

        Note: GH_TOKEN is optional. Authentication is validated by setup_auth() instead.
        This method is kept for consistency with the base class but returns empty list.

        Returns:
            List of missing environment variable names (empty list for GitHub)
        """
        # No required environment variables for GitHub platform
        # Authentication is handled by setup_auth() which checks both GH_TOKEN and gh CLI auth
        return []
