"""PR Review Agent configuration."""

from google.adk.agents import Agent


def create_review_agent() -> Agent:
    """
    Initialize the PR review agent with Gemini 2.5 Flash.

    Returns:
        Configured Agent instance for code review
    """
    return Agent(
        model='gemini-2.5-flash',
        name='pr_reviewer',
        instruction="""You are a code reviewer analyzing a pull request.

Review the PR for:
- Obvious bugs or logic errors
- Code quality issues (complexity, readability)
- Potential security issues
- Missing error handling
- Best practice violations

Provide a concise review summary with:
1. Overall assessment (Looks good / Needs work / Has issues)
2. Key findings (list 3-5 most important issues)
3. Positive observations (what's done well)

Keep feedback constructive and actionable.
Format your response in markdown for GitHub.
"""
    )
