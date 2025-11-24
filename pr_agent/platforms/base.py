"""Abstract base class for Git hosting platform integrations."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List


class GitPlatform(ABC):
    """Abstract base class for Git hosting platform operations.

    This class defines the interface that all Git platform implementations
    (GitHub, GitLab, Bitbucket, etc.) must implement to support PR/MR reviews.
    """

    @abstractmethod
    def get_pr_info(self, repo: str, pr_number: int) -> Dict:
        """Fetch pull/merge request metadata.

        Args:
            repo: Repository identifier (e.g., 'owner/repo' for GitHub,
                  'group/project' for GitLab)
            pr_number: Pull/merge request number

        Returns:
            Dictionary containing PR metadata with at least:
            - title: PR/MR title
            - body: PR/MR description
            - author: Author information (dict with 'login' key)
            - headRefName: Source branch name
            - baseRefName: Target branch name

        Raises:
            subprocess.CalledProcessError: If the CLI command fails
            Exception: For other errors (network, auth, etc.)
        """
        pass

    @abstractmethod
    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the full diff for a pull/merge request.

        Args:
            repo: Repository identifier
            pr_number: Pull/merge request number

        Returns:
            String containing the full unified diff of all changes

        Raises:
            subprocess.CalledProcessError: If the CLI command fails
            Exception: For other errors
        """
        pass

    @abstractmethod
    def post_pr_comment(self, repo: str, pr_number: int, body: str) -> None:
        """Post a comment on a pull/merge request.

        Args:
            repo: Repository identifier
            pr_number: Pull/merge request number
            body: Comment text (supports markdown)

        Raises:
            subprocess.CalledProcessError: If the CLI command fails
            Exception: For other errors
        """
        pass

    @abstractmethod
    def get_pr_number_from_event(self) -> Optional[int]:
        """Extract PR/MR number from CI/CD environment context.

        Each platform has different environment variables in their CI/CD systems:
        - GitHub Actions: GITHUB_EVENT_PATH contains event JSON
        - GitLab CI: CI_MERGE_REQUEST_IID contains MR number

        Returns:
            PR/MR number if running in CI/CD context, None otherwise
        """
        pass

    @abstractmethod
    def setup_auth(self) -> None:
        """Set up authentication for the platform CLI tool.

        Each platform may require different authentication setup:
        - GitHub: Typically relies on gh auth login (done manually/locally)
        - GitLab: Requires glab auth login with CI_JOB_TOKEN in CI/CD

        This method should handle both CI/CD and local development scenarios.

        Raises:
            subprocess.CalledProcessError: If the auth command fails
            Exception: For other authentication errors
        """
        pass

    def get_platform_name(self) -> str:
        """Return the name of this platform (for logging/debugging).

        Returns:
            Platform name (e.g., 'GitHub', 'GitLab')
        """
        return self.__class__.__name__.replace('Platform', '')

    @abstractmethod
    def validate_environment_variables(self) -> List[str]:
        """Validate platform-specific environment variables.

        Each platform should check for its required environment variables
        and return a list of any that are missing.

        The validation should check:
        - Platform-specific repository identifier (if generic REPOSITORY not set)
        - Platform-specific PR/MR number (if generic PR_NUMBER not set)
        - Any other platform-specific required variables

        Returns:
            List of missing environment variable names (empty list if all present)
        """
        pass
