"""ADK tool functions for PR Review Agent.

These tools wrap the platform classes to provide PR/MR data fetching
capabilities for the interactive ADK dev UI.
"""

import logging

from pr_agent.platforms import GitPlatform

logger = logging.getLogger(__name__)


class PRTools:
    """Tools for fetching PR/MR data from Git hosting platforms.

    This class wraps a platform instance to provide PR/MR data fetching
    capabilities with consistent error handling.
    """

    def __init__(self, platform: GitPlatform):
        """Initialize PRTools with a platform instance.

        Args:
            platform: An authenticated GitPlatform instance (e.g., GitHubPlatform
                     or GitLabPlatform). The platform should already have
                     setup_auth() called.
        """
        self._platform = platform
        self._platform_name = platform.__class__.__name__.replace("Platform", "").lower()
        logger.debug(f"PRTools initialized with platform: {self._platform_name}")

    @property
    def platform(self) -> GitPlatform:
        """Get the underlying platform instance."""
        return self._platform

    @property
    def platform_name(self) -> str:
        """Get the platform name (e.g., 'github' or 'gitlab')."""
        return self._platform_name

    def get_pr_info(self, repo: str, pr_number: int) -> dict:
        """Fetch pull request or merge request metadata.

        Use this tool to retrieve information about a PR/MR including title,
        description, author, and branch names.

        Args:
            repo: Repository identifier (e.g., 'owner/repo' for GitHub,
                  'group/project' for GitLab)
            pr_number: The pull request or merge request number

        Returns:
            Dictionary containing PR metadata with keys:
            - title: PR/MR title
            - body: PR/MR description
            - author: Author info with 'login' key
            - headRefName: Source branch name
            - baseRefName: Target branch name
            - status: 'success' or 'error'
            - error: Error message (only present on failure)
        """
        try:
            pr_data = self._platform.get_pr_info(repo, pr_number)
            return {
                "status": "success",
                "platform": self._platform_name,
                "repository": repo,
                "pr_number": pr_number,
                **pr_data,
            }
        except RuntimeError as e:
            logger.error(f"Failed to fetch PR info: {e}")
            return {
                "status": "error",
                "error": str(e),
                "platform": self._platform_name,
                "repository": repo,
                "pr_number": pr_number,
            }
        except Exception as e:
            logger.error(f"Failed to fetch PR info: {e}")
            return {
                "status": "error",
                "error": str(e),
                "platform": self._platform_name,
                "repository": repo,
                "pr_number": pr_number,
            }

    def get_pr_diff(self, repo: str, pr_number: int) -> dict:
        """Fetch the full diff for a pull request or merge request.

        Use this tool to retrieve the complete code changes in a PR/MR.
        The diff is returned in unified diff format.

        Args:
            repo: Repository identifier (e.g., 'owner/repo' for GitHub,
                  'group/project' for GitLab)
            pr_number: The pull request or merge request number

        Returns:
            Dictionary containing:
            - diff: The unified diff content as a string
            - diff_length: Length of the diff in characters
            - status: 'success' or 'error'
            - error: Error message (only present on failure)
        """
        try:
            diff = self._platform.get_pr_diff(repo, pr_number)
            return {
                "status": "success",
                "platform": self._platform_name,
                "repository": repo,
                "pr_number": pr_number,
                "diff": diff,
                "diff_length": len(diff),
            }
        except RuntimeError as e:
            logger.error(f"Failed to fetch PR diff: {e}")
            return {
                "status": "error",
                "error": str(e),
                "platform": self._platform_name,
                "repository": repo,
                "pr_number": pr_number,
            }
        except Exception as e:
            logger.error(f"Failed to fetch PR diff: {e}")
            return {
                "status": "error",
                "error": str(e),
                "platform": self._platform_name,
                "repository": repo,
                "pr_number": pr_number,
            }
