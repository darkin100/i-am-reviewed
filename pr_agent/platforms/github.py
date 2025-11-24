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

    def get_pr_number_from_event(self) -> Optional[int]:
        """Extract PR number from GitHub Actions event context.

        Reads the GITHUB_EVENT_PATH file which contains the webhook event payload
        in GitHub Actions. The PR number is extracted from the 'pull_request' field.

        Returns:
            PR number if running in GitHub Actions with a PR event, None otherwise
        """
        event_path = os.getenv('GITHUB_EVENT_PATH')
        if not event_path:
            return None

        try:
            with open(event_path, 'r') as f:
                event_data = json.load(f)
                # Extract PR number from the event
                if 'pull_request' in event_data:
                    return event_data['pull_request']['number']
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not extract PR number from event: {e}")

        return None

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
        - GitHub Actions context: GITHUB_EVENT_PATH (can extract PR number)

        Returns:
            List of missing environment variable names (empty list if all present)
        """
        missing_vars = []

        # Check PR number
        github_event_path = os.getenv('GITHUB_EVENT_PATH')

        # PR number can come from generic var, GitHub-specific var, or event file
        if not github_event_path:
            missing_vars.append('PR_NUMBER, or GITHUB_EVENT_PATH')

        return missing_vars
