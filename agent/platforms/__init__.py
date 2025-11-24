"""Platform abstraction for different Git hosting providers."""

from agent.platforms.base import GitPlatform
from agent.platforms.github import GitHubPlatform
from agent.platforms.gitlab import GitLabPlatform


def get_platform(provider: str) -> GitPlatform:
    """Factory function to get the appropriate platform implementation.

    Args:
        provider: The Git hosting provider name ('github' or 'gitlab')

    Returns:
        An instance of the appropriate GitPlatform subclass

    Raises:
        ValueError: If the provider is not supported
    """
    providers = {
        'github': GitHubPlatform,
        'gitlab': GitLabPlatform,
    }

    provider_lower = provider.lower()
    if provider_lower not in providers:
        supported = ', '.join(providers.keys())
        raise ValueError(
            f"Unsupported provider: '{provider}'. "
            f"Supported providers: {supported}"
        )

    return providers[provider_lower]()


__all__ = ['GitPlatform', 'GitHubPlatform', 'GitLabPlatform', 'get_platform']
