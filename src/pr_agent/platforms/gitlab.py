"""GitLab platform implementation using GitLab CLI."""

import json
import os
import subprocess
from typing import Dict, Optional

from pr_agent.logging_config import get_logger
from pr_agent.platforms.base import GitPlatform
from pr_agent.tracing_config import traced

logger = get_logger(__name__)


class GitLabPlatform(GitPlatform):
    """GitLab platform implementation using glab CLI.

    This implementation uses the GitLab CLI (glab) to interact with GitLab's API.
    """

    def __init__(self):
        """Initialize GitLab platform with authentication state."""
        super().__init__()
        self._gitlab_token: Optional[str] = None
        self._auth_method: Optional[str] = None

    def _get_subprocess_env(self) -> Dict[str, str]:
        """Get environment dict for subprocess calls.

        Returns environment variables to pass to subprocess, including GITLAB_TOKEN
        when using token-based authentication.

        Returns:
            Dictionary of environment variables
        """
        # Start with current environment
        env = os.environ.copy()

        # Add GITLAB_TOKEN if using token-based auth
        if self._auth_method == "token" and self._gitlab_token:
            env["GITLAB_TOKEN"] = self._gitlab_token

        return env

    @traced("gitlab.get_pr_info")
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
        cmd = ["glab", "mr", "view", str(pr_number), "-R", repo, "-F", "json"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=self._get_subprocess_env()
        )

        # Parse GitLab MR data and normalize to GitHub-compatible format
        mr_data = json.loads(result.stdout)

        # Normalize the structure to match GitHub's format
        return {
            "title": mr_data.get("title", ""),
            "body": mr_data.get("description", ""),
            "author": {"login": mr_data.get("author", {}).get("username", "")},
            "headRefName": mr_data.get("source_branch", ""),
            "baseRefName": mr_data.get("target_branch", ""),
        }

    @traced("gitlab.get_pr_diff")
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
        cmd = ["glab", "mr", "diff", str(pr_number), "-R", repo]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=self._get_subprocess_env()
        )

        return result.stdout

    @traced("gitlab.post_pr_comment")
    def post_pr_comment(self, repo: str, pr_number: int, body: str) -> None:
        """Post a comment on the MR using GitLab CLI.

        Args:
            repo: Repository in format 'group/project'
            pr_number: Merge request IID
            body: Comment text (supports markdown)

        Raises:
            subprocess.CalledProcessError: If the glab command fails
        """
        cmd = ["glab", "mr", "note", str(pr_number), "-R", repo, "--message", body]

        subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=self._get_subprocess_env()
        )

    def setup_auth(self) -> None:
        """Set up GitLab CLI authentication.

        Supports two authentication methods:
        - CI/CD: Uses GITLAB_TOKEN environment variable if available
        - Local: Falls back to glab CLI's local authentication (via 'glab auth login')

        Note: When using GITLAB_TOKEN, the token is passed via environment variable
        rather than command-line argument for security (avoids exposure in process listings).

        Raises:
            RuntimeError: If neither authentication method is available
        """
        # Check if GITLAB_TOKEN is available (CI mode)
        gitlab_token = os.getenv("GITLAB_TOKEN")

        if gitlab_token:
            self._gitlab_token = gitlab_token
            self._auth_method = "token"
            ci_server_host = os.getenv("CI_SERVER_HOST", "gitlab.com")
            logger.info(
                "GitLab authentication configured",
                extra={"context": {"method": "GITLAB_TOKEN", "mode": "CI", "host": ci_server_host}},
            )
            return

        # Check if glab CLI is authenticated (local mode)
        try:
            result = subprocess.run(
                ["glab", "auth", "status"], capture_output=True, text=True, check=False
            )

            # glab auth status returns 0 if authenticated
            if result.returncode == 0:
                self._auth_method = "cli"
                logger.info(
                    "GitLab authentication configured",
                    extra={"context": {"method": "glab_cli", "mode": "interactive"}},
                )
                return
        except FileNotFoundError:
            raise RuntimeError(
                "GitLab CLI (glab) is not installed. "
                "Please install it from https://gitlab.com/gitlab-org/cli"
            )

        # Neither authentication method available
        raise RuntimeError(
            "No GitLab authentication available. Please either:\n"
            "  - Set GITLAB_TOKEN environment variable (for CI/CD), or\n"
            "  - Run 'glab auth login' (for local development)"
        )
