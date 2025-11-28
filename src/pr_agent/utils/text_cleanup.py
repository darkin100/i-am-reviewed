"""Text cleanup utilities for processing AI-generated content."""

import re


def strip_markdown_wrapper(text: str) -> str:
    """Remove markdown code block wrappers from text.

    The AI model sometimes wraps its entire response in markdown code blocks like:
    ```markdown
    actual content here
    ```

    This causes rendering issues on GitHub/GitLab, as the entire comment
    is displayed as a code block instead of formatted markdown.

    This function detects and removes such wrappers while preserving:
    - Legitimate code blocks within the content
    - Already clean text (no-op)
    - The actual formatting and structure of the content

    Args:
        text: Input text that may be wrapped in markdown code blocks

    Returns:
        Cleaned text with outer markdown wrapper removed

    Examples:
        >>> strip_markdown_wrapper("```markdown\\n## Review\\nLooks good\\n```")
        "## Review\\nLooks good"

        >>> strip_markdown_wrapper("```\\n## Review\\nLooks good\\n```")
        "## Review\\nLooks good"

        >>> strip_markdown_wrapper("## Review\\nLooks good")
        "## Review\\nLooks good"
    """
    if not text or not isinstance(text, str):
        return text

    # Strip leading/trailing whitespace to normalize
    text = text.strip()

    # Pattern 1: Full wrapper with closing ```
    # Matches: ```markdown or ``` at start, and ``` at end (with flexible whitespace)
    pattern_full = r'^```(?:markdown|md)?\s*\n(.*?)(?:\n```\s*)?$'

    # Check if text starts with markdown code block opener
    if re.match(r'^```(?:markdown|md)?\s*\n', text):
        match = re.match(pattern_full, text, re.DOTALL)
        if match:
            content = match.group(1)
            # Remove trailing ``` if present at end of content
            content = re.sub(r'\n?```\s*$', '', content)
            # Recursively check for more wrappers
            return strip_markdown_wrapper(content.strip())

    # No wrapper found, return as-is
    return text
