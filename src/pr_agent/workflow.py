"""Main execution script for PR review agent."""

import argparse
import asyncio
import logging
import os
import subprocess
import sys

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from pr_agent.config import setup_environment, setup_google_cloud_auth
from pr_agent.logging_config import setup_logging
from pr_agent.platforms import get_platform
from pr_agent.tools import get_pr_diff, get_pr_info
from pr_agent.tracing_config import get_tracer, setup_tracing
from pr_agent.utils import strip_markdown_wrapper

# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)


def get_repository_identifier() -> str:
    """Get repository identifier from environment variables.

    Returns:
        Repository identifier string (e.g., 'owner/repo')

    Note:
        Assumes REPOSITORY has been validated by ValidateEnvironmentVariables().
    """
    # REPOSITORY is validated by setup_environment() before this is called
    repo = os.getenv("REPOSITORY")
    assert repo is not None, "REPOSITORY must be set"
    return repo


def get_pr_number() -> int:
    """Get PR/MR number from environment variables.

    Returns:
        PR/MR number as integer

    Raises:
        SystemExit: If PR_NUMBER is not a valid integer

    Note:
        Assumes PR_NUMBER presence has been validated by ValidateEnvironmentVariables().
        Only validates the integer conversion here.
    """
    pr_number_str = os.getenv("PR_NUMBER")

    if pr_number_str is None:
        logger.error("PR_NUMBER environment variable is not set")
        sys.exit(1)

    try:
        return int(pr_number_str)
    except ValueError:
        logger.error(
            "PR/MR number must be a valid integer",
            extra={"context": {"received_value": pr_number_str}},
        )
        sys.exit(1)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="AI-powered Pull/Merge Request Review Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review GitHub PR
  python -m agent.workflow --provider github

  # Review GitLab MR
  python -m agent.workflow --provider gitlab

Environment Variables:
  REPOSITORY
  PR_NUMBER
  GOOGLE_CLOUD_PROJECT - Google Cloud project ID
  GOOGLE_CLOUD_LOCATION - Google Cloud location (e.g., europe-west2)
        """,
    )

    parser.add_argument(
        "--provider",
        type=str,
        required=True,
        choices=["github", "gitlab"],
        help="Git hosting provider (github or gitlab)",
    )

    return parser.parse_args()


def create_review_agent() -> LlmAgent:
    """Create and configure the PR review agent.

    Returns:
        Configured LlmAgent for PR reviews
    """
    system_instruction = """You are a code review assistant that helps developers analyze pull requests and merge requests.

    ## Your Capabilities
    You have access to tools for fetching PR/MR data from GitHub and GitLab:
    - get_pr_info: Fetch PR/MR metadata (title, description, author, branches)
    - get_pr_diff: Fetch the full code diff

    ## How to Help Users

    1. When a user provides a PR reference (URL, repo+number, etc.), use the tools to fetch the PR data
    2. Always fetch BOTH the PR info AND the diff before providing a review
    3. Analyze the code changes thoroughly
    4. Provide a structured review covering:
    - Overall assessment (Looks good / Needs work / Has issues)
    - Key findings (3-5 most important observations)
    - Potential bugs or logic errors
    - Code quality issues (complexity, readability)
    - Security concerns
    - Missing error handling
    - Positive observations (what's done well)

## Output Format

Format your reviews in clear markdown. Be constructive and actionable in your feedback.
Keep feedback concise but thorough."""

    return LlmAgent(
        model="gemini-2.5-flash",
        name="pr_review_agent",
        description="An AI agent that reviews pull requests from GitHub and GitLab for code quality, bugs, and best practices.",
        instruction=system_instruction,
        tools=[get_pr_info, get_pr_diff],
        generate_content_config=types.GenerateContentConfig(temperature=0.7),
    )


async def run_review_agent(prompt: str) -> str | None:
    """Run the PR review agent with the given prompt.

    Args:
        prompt: The PR details to review

    Returns:
        The review text from the agent, or None if no response was generated
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("llm_agent_execution") as span:
        span.set_attribute("prompt_length", len(prompt))

        agent = create_review_agent()
        runner = InMemoryRunner(agent=agent, app_name="pr_review")

        events = await runner.run_debug(prompt)

        # Extract text from the last event's content
        # run_debug() returns a list of Event objects
        for event in reversed(events):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        span.set_attribute("response_length", len(part.text))
                        return part.text

        return None


def workflow():
    logger.info("Initiating Workflow")

    try:
        # Parse command-line arguments
        args = parse_arguments()

        logger.info("Arguments parsed", extra={"context": {"provider": args.provider}})

        # Get platform implementation
        try:
            platform = get_platform(args.provider)
            logger.info(
                "Platform selected", extra={"context": {"platform": platform.get_platform_name()}}
            )
        except ValueError as e:
            logger.error(f"Platform initialization failed: {e}")
            sys.exit(1)

        # Validate environment variables (generic + platform-specific)
        setup_environment()

        # Set up Google Cloud authentication
        setup_google_cloud_auth()

        # Initialize tracing
        enable_cloud_trace = os.getenv("ENABLE_CLOUD_TRACE", "true").lower() == "true"
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        assert project_id is not None, "GOOGLE_CLOUD_PROJECT must be set"
        tracer = setup_tracing(project_id=project_id, enable_cloud_trace=enable_cloud_trace)

        # Set up platform authentication
        platform.setup_auth()

        # Get repository identifier
        repo = get_repository_identifier()
        logger.info("Repository identified", extra={"context": {"repository": repo}})

        # Get PR/MR number
        pr_number = get_pr_number()
        logger.info(
            "Starting PR review", extra={"context": {"repository": repo, "pr_number": pr_number}}
        )

        # Start the main workflow span
        with tracer.start_as_current_span("pr_review_workflow") as root_span:
            root_span.set_attribute("repository", repo)
            root_span.set_attribute("pr_number", pr_number)
            root_span.set_attribute("platform", platform.get_platform_name())

            # Create review prompt
            prompt = f"""Based on the provided repository and PR/MR number can you please review this pull request?

Repo: {repo}
PR/MR Number: {pr_number}

Provide your code review."""

            # Get agent review using ADK Agent
            logger.info("Generating review with AI")
            logger.debug("LLM prompt", extra={"context": {"prompt": prompt}})

            review_text = asyncio.run(run_review_agent(prompt))

            if not review_text:
                logger.error("No response received from model")
                sys.exit(1)

            logger.debug(
                "LLM response received",
                extra={
                    "context": {"response_length": len(review_text), "review_text": review_text}
                },
            )

            # Clean up any markdown code block wrappers that the AI might have added
            review_text = strip_markdown_wrapper(review_text)

            # Post review comment using platform abstraction
            logger.info("Posting review comment to PR/MR")
            logger.debug(
                "Generated review content", extra={"context": {"review_text": review_text}}
            )
            platform.post_pr_comment(repo, pr_number, review_text)

            logger.info("Review successfully posted", extra={"context": {"pr_number": pr_number}})

    except subprocess.CalledProcessError as e:
        logger.error(
            "CLI command failed",
            extra={"context": {"error": str(e), "stdout": e.stdout, "stderr": e.stderr}},
            exc_info=True,
        )
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    workflow()
