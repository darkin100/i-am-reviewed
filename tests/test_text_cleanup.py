"""Tests for text cleanup utilities."""

from pr_agent.utils.text_cleanup import strip_markdown_wrapper


class TestStripMarkdownWrapper:
    """Test cases for the strip_markdown_wrapper function."""

    def test_strip_markdown_identifier_wrapper(self):
        """Test removing wrapper with 'markdown' identifier."""
        input_text = "```markdown\n## Review Summary\nLooks good!\n```"
        expected = "## Review Summary\nLooks good!"
        assert strip_markdown_wrapper(input_text) == expected

    def test_strip_generic_wrapper(self):
        """Test removing generic code block wrapper."""
        input_text = "```\n## Review Summary\nLooks good!\n```"
        expected = "## Review Summary\nLooks good!"
        assert strip_markdown_wrapper(input_text) == expected

    def test_no_wrapper_unchanged(self):
        """Test that text without wrapper is unchanged."""
        input_text = "## Review Summary\nLooks good!"
        expected = "## Review Summary\nLooks good!"
        assert strip_markdown_wrapper(input_text) == expected

    def test_preserve_internal_code_blocks(self):
        """Test that code blocks within content are preserved."""
        input_text = """```markdown
## Review Summary

Here's some code:

```python
def hello():
    print("world")
```

Overall looks good!
```"""
        expected = """## Review Summary

Here's some code:

```python
def hello():
    print("world")
```

Overall looks good!"""
        assert strip_markdown_wrapper(input_text) == expected

    def test_nested_code_blocks_preserved(self):
        """Test that internal code blocks are NOT stripped (only outermost wrapper)."""
        # This tests the fix for the recursive stripping bug
        # Inner markdown block should be preserved as legitimate content
        input_text = (
            "```markdown\nHere's a template:\n\n```markdown\n## Heading\n```\n\nUse it wisely.\n```"
        )
        expected = "Here's a template:\n\n```markdown\n## Heading\n```\n\nUse it wisely."
        assert strip_markdown_wrapper(input_text) == expected

    def test_empty_string(self):
        """Test handling of empty string."""
        assert strip_markdown_wrapper("") == ""

    def test_none_input(self):
        """Test handling of None input."""
        assert strip_markdown_wrapper(None) is None

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled correctly."""
        input_text = "  ```markdown\n## Review\n```  "
        expected = "## Review"
        assert strip_markdown_wrapper(input_text) == expected

    def test_multiline_content(self):
        """Test handling of multiline content with complex formatting."""
        input_text = """```markdown
# Code Review

## Overall Assessment
Looks good with minor issues.

## Key Findings
1. Missing error handling
2. No input validation
3. Performance could be improved

## Positive Observations
- Clean code structure
- Good naming conventions
```"""
        expected = """# Code Review

## Overall Assessment
Looks good with minor issues.

## Key Findings
1. Missing error handling
2. No input validation
3. Performance could be improved

## Positive Observations
- Clean code structure
- Good naming conventions"""
        assert strip_markdown_wrapper(input_text) == expected

    def test_wrapper_with_extra_whitespace(self):
        """Test wrapper with extra whitespace after opening backticks."""
        input_text = "```markdown  \n## Review\nLooks good!\n```"
        expected = "## Review\nLooks good!"
        assert strip_markdown_wrapper(input_text) == expected

    def test_partial_wrapper_unchanged(self):
        """Test that partial/incomplete wrappers are left unchanged."""
        # Only opening backticks
        input_text = "```markdown\n## Review\nLooks good!"
        assert strip_markdown_wrapper(input_text) == input_text

        # Only closing backticks
        input_text = "## Review\nLooks good!\n```"
        assert strip_markdown_wrapper(input_text) == input_text

    def test_real_world_example(self):
        """Test with a realistic AI-generated review."""
        input_text = """```markdown
## Code Review Summary

### Overall Assessment
**Needs work** - There are several issues that should be addressed.

### Key Findings

1. **Missing Error Handling** (Line 45)
   - The database connection doesn't handle failures
   - Could cause unhandled exceptions in production

2. **Security Issue** (Line 78)
   - SQL query uses string concatenation
   - Vulnerable to SQL injection attacks

3. **Performance Concern** (Line 123)
   - N+1 query problem in the loop
   - Consider using batch operations

### Positive Observations

- Good use of type hints
- Clear function naming
- Comprehensive docstrings

### Recommendations

Please address the security issue before merging.
```"""
        expected = """## Code Review Summary

### Overall Assessment
**Needs work** - There are several issues that should be addressed.

### Key Findings

1. **Missing Error Handling** (Line 45)
   - The database connection doesn't handle failures
   - Could cause unhandled exceptions in production

2. **Security Issue** (Line 78)
   - SQL query uses string concatenation
   - Vulnerable to SQL injection attacks

3. **Performance Concern** (Line 123)
   - N+1 query problem in the loop
   - Consider using batch operations

### Positive Observations

- Good use of type hints
- Clear function naming
- Comprehensive docstrings

### Recommendations

Please address the security issue before merging."""
        assert strip_markdown_wrapper(input_text) == expected

    def test_non_string_input(self):
        """Test handling of non-string input types."""
        assert strip_markdown_wrapper(123) == 123
        assert strip_markdown_wrapper([]) == []
        assert strip_markdown_wrapper({}) == {}
