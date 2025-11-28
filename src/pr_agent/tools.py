"""ADK tool functions for PR Review Agent.

These tools wrap the platform classes to provide PR/MR data fetching
capabilities for the interactive ADK dev UI.
"""

from typing import Dict, Optional

from pr_agent.platforms import get_platform, GitPlatform
from pr_agent.logging_config import get_logger

logger = get_logger(__name__)

# Cached platform instances to avoid re-authentication on each tool call
_platform_cache: Dict[str, GitPlatform] = {}


def _get_or_create_platform(platform: str) -> GitPlatform:
    """Get or create a platform instance with authentication.

    Args:
        platform: Platform name ('github' or 'gitlab')

    Returns:
        Authenticated platform instance

    Raises:
        ValueError: If platform is not supported
        RuntimeError: If authentication fails
    """
    platform_lower = platform.lower()
    if platform_lower not in _platform_cache:
        plat = get_platform(platform_lower)
        plat.setup_auth()
        _platform_cache[platform_lower] = plat
    return _platform_cache[platform_lower]


def get_pr_info(platform: str, repo: str, pr_number: int) -> Dict:
    """Fetch pull request or merge request metadata.

    Use this tool to retrieve information about a PR/MR including title,
    description, author, and branch names.

    Args:
        platform: The Git hosting platform ('github' or 'gitlab')
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
        plat = _get_or_create_platform(platform)
        pr_data = plat.get_pr_info(repo, pr_number)
        return {
            "status": "success",
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number,
            **pr_data
        }
    except ValueError as e:
        logger.error(f"Invalid platform: {e}")
        return {
            "status": "error",
            "error": f"Invalid platform '{platform}'. Use 'github' or 'gitlab'.",
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number
        }
    except RuntimeError as e:
        logger.error(f"Authentication failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number
        }
    except Exception as e:
        logger.error(f"Failed to fetch PR info: {e}")
        return {
            "status": "error",
            "error": str(e),
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number
        }


def get_pr_diff(platform: str, repo: str, pr_number: int) -> Dict:
    """Fetch the full diff for a pull request or merge request.

    Use this tool to retrieve the complete code changes in a PR/MR.
    The diff is returned in unified diff format.

    Args:
        platform: The Git hosting platform ('github' or 'gitlab')
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
        plat = _get_or_create_platform(platform)
        diff = plat.get_pr_diff(repo, pr_number)
        return {
            "status": "success",
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number,
            "diff": diff,
            "diff_length": len(diff)
        }
    except ValueError as e:
        logger.error(f"Invalid platform: {e}")
        return {
            "status": "error",
            "error": f"Invalid platform '{platform}'. Use 'github' or 'gitlab'.",
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number
        }
    except RuntimeError as e:
        logger.error(f"Authentication failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number
        }
    except Exception as e:
        logger.error(f"Failed to fetch PR diff: {e}")
        return {
            "status": "error",
            "error": str(e),
            "platform": platform,
            "repository": repo,
            "pr_number": pr_number
        }
