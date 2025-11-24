"""GitLab platform implementation using GitLab CLI."""

import os
import json
import subprocess
from typing import Dict, Optional, List

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

    def setup_auth(self) -> None:
        """Set up GitLab CLI authentication.

        Authentication priority:
        1. GITLAB_TOKEN (Personal Access Token) - preferred for full API access
        2. CI_JOB_TOKEN - fallback for CI/CD (has limited API access)
        3. Assume already authenticated locally via 'glab auth login'

        Raises:
            subprocess.CalledProcessError: If the glab auth command fails
        """
        # Get environment variables
        gitlab_token = os.getenv('GITLAB_TOKEN')
        ci_job_token = os.getenv('CI_JOB_TOKEN')
        ci_server_host = os.getenv('CI_SERVER_HOST', 'gitlab.com')
        ci_server_protocol = os.getenv('CI_SERVER_PROTOCOL', 'https')
        ci_server_url = os.getenv('CI_SERVER_URL')

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

        # Priority 2: Use CI_JOB_TOKEN if available (limited API access)
        elif ci_job_token and ci_server_host:
            print(f"Authenticating glab with CI_JOB_TOKEN for {ci_server_host}")
            print("Warning: CI_JOB_TOKEN has limited API access. Some operations may fail.")

            cmd = [
                'glab', 'auth', 'login',
                '--job-token', ci_job_token,
                '--hostname', ci_server_host,
                '--api-protocol', ci_server_protocol
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            print("GitLab CLI authenticated successfully with CI_JOB_TOKEN")

        # Priority 3: Assume already authenticated locally
        else:
            print("Running locally - assuming glab is already authenticated via 'glab auth login'")

    def validate_environment_variables(self) -> List[str]:
        """Validate GitLab-specific environment variables.

        Checks for repository identifier and MR number, using either:
        - Generic variables: REPOSITORY, PR_NUMBER
        - GitLab-specific: CI_PROJECT_PATH, CI_MERGE_REQUEST_IID (if generic not set)

        Also validates GitLab authentication variables:
        - GITLAB_TOKEN (preferred) or CI_JOB_TOKEN (in CI/CD)

        Returns:
            List of missing environment variable names (empty list if all present)
        """
        missing_vars = []

        # Check repository identifier
        repository = os.getenv('REPOSITORY')
        ci_project_path = os.getenv('CI_PROJECT_PATH')

        if not repository and not ci_project_path:
            missing_vars.append('REPOSITORY or CI_PROJECT_PATH')

        # Check MR number
        pr_number = os.getenv('PR_NUMBER')
        ci_merge_request_iid = os.getenv('CI_MERGE_REQUEST_IID')

        if not pr_number and not ci_merge_request_iid:
            missing_vars.append('PR_NUMBER or CI_MERGE_REQUEST_IID')

        # Note: GITLAB_TOKEN and CI_JOB_TOKEN are optional for local dev
        # (user may already be authenticated via 'glab auth login')
        # But warn if neither is present in CI/CD context
        gitlab_token = os.getenv('GITLAB_TOKEN')
        ci_job_token = os.getenv('CI_JOB_TOKEN')

        # If we're in CI (CI_MERGE_REQUEST_IID is set) and no tokens available
        if ci_merge_request_iid and not gitlab_token and not ci_job_token:
            missing_vars.append('GITLAB_TOKEN or CI_JOB_TOKEN (required in CI/CD)')

        return missing_vars
