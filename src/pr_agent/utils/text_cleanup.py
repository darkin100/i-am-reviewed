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

    # Check for complete markdown wrapper:
    # - Must start with ```markdown or ```md or ``` followed by newline
    # - Must end with ``` (possibly followed by whitespace)
    # Only strip if we have BOTH opening and closing backticks
    if not re.match(r"^```(?:markdown|md)?\s*\n", text):
        return text

    if not re.search(r"\n```\s*$", text):
        return text

    # We have a complete wrapper - extract content between them
    # Use a greedy match for content to capture everything between
    # the opening and the LAST closing ```
    pattern = r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        content = match.group(1)
        # Only strip the outermost wrapper - do not recurse
        # to avoid stripping legitimate internal code blocks
        return content.strip()

    # No valid wrapper found, return as-is
    return text
