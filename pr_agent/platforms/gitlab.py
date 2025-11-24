"""GitLab platform implementation using GitLab CLI."""

import os
import json
import subprocess
from typing import Dict, Optional, List

from pr_agent.platforms.base import GitPlatform


class GitLabPlatform(GitPlatform):
    """GitLab platform implementation using glab CLI.

    This implementation uses the GitLab CLI (glab) to interact with GitLab's API.
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
            '-F', 'json'
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

    def setup_auth(self) -> None:
        """Set up GitLab CLI authentication.

        Authentication priority:
        1. GITLAB_TOKEN (Personal Access Token) - preferred for full API access

        Raises:
            subprocess.CalledProcessError: If the glab auth command fails
        """
        # Get environment variables
        gitlab_token = os.getenv('GITLAB_TOKEN')
        ci_server_host = os.getenv('CI_SERVER_HOST', 'gitlab.com')

        # Priority 1: Use GITLAB_TOKEN (Personal Access Token) if available
        if gitlab_token:
            print(f"Authenticating glab with GITLAB_TOKEN (PAT) for {ci_server_host}")

            cmd = [
                'glab', 'auth', 'login',
                '--token', gitlab_token,
                '--hostname', ci_server_host
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            print("GitLab CLI authenticated successfully with PAT")

        # Priority 2: Assume already authenticated locally
        else:
            print("Running locally - assuming glab is already authenticated via 'glab auth login'")

    def validate_environment_variables(self) -> List[str]:
        """Validate GitLab-specific environment variables.

        Returns:
            List of missing environment variable names (empty list if all present)
        """
        missing_vars = []

        repository = os.getenv('REPOSITORY')

        if not repository:
            missing_vars.append('REPOSITORY')

        pr_number = os.getenv('PR_NUMBER')

        if not pr_number:
            missing_vars.append('PR_NUMBER')

        gitlab_token = os.getenv('GITLAB_TOKEN')

        if not gitlab_token:
            missing_vars.append('GITLAB_TOKEN')


        return missing_vars
