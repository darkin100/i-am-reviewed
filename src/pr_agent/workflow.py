"""Main execution script for PR review agent."""

import argparse
import asyncio
import os
import subprocess
import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from pr_agent.config import setup_google_cloud_auth
from pr_agent.logging_config import get_logger, setup_logging
from pr_agent.platforms import get_platform
from pr_agent.tools import get_pr_diff, get_pr_info
from pr_agent.tracing_config import get_tracer, setup_tracing
from pr_agent.utils import strip_markdown_wrapper

# Initialize logging first
setup_logging()
logger = get_logger(__name__)


def get_repository_identifier() -> str:
    """Get repository identifier from environment variables.

    Returns:
        Repository identifier string (e.g., 'owner/repo')

    Note:
        Assumes REPOSITORY has been validated by ValidateEnvironmentVariables().
    """
    return os.getenv("REPOSITORY")


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

    try:
        return int(pr_number_str)
    except (ValueError, TypeError):
        logger.error(
            "PR/MR number must be a valid integer",
            extra={"context": {"received_value": pr_number_str}},
        )
        sys.exit(1)


def ValidateEnvironmentVariables(platform=None):
    """Validate all required environment variables.

    Validates generic environment variables required by all platforms,
    and delegates platform-specific validation to the platform instance.

    Args:
        platform: Platform instance to validate platform-specific variables (optional)

    Raises:
        SystemExit: If any required environment variables are missing
    """
    missing_vars = []

    # Validate Google Cloud environment variables
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        missing_vars.append("GOOGLE_CLOUD_PROJECT")

    if not os.getenv("GOOGLE_CLOUD_LOCATION"):
        missing_vars.append("GOOGLE_CLOUD_LOCATION")

    if not os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"):
        os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "true"

    if not os.getenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"):
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"

    # Enable Vertex AI backend for ADK
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

    # Validate generic environment variables
    if not os.getenv("REPOSITORY"):
        missing_vars.append("REPOSITORY (or platform-specific equivalent)")
    if not os.getenv("PR_NUMBER"):
        missing_vars.append("PR_NUMBER (or platform-specific equivalent)")

    # Report all missing variables
    if missing_vars:
        logger.error(
            "Missing required environment variables",
            extra={"context": {"missing_vars": missing_vars}},
        )
        sys.exit(1)

    logger.info("Environment variables validated successfully")


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


async def run_review_agent(prompt: str) -> str:
    """Run the PR review agent with the given prompt.

    Args:
        prompt: The PR details to review

    Returns:
        The review text from the agent
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
    """Run PR review workflow."""
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Get platform implementation
        try:
            platform = get_platform(args.provider)
            logger.info(
                "Platform selected", extra={"context": {"platform": platform.get_platform_name()}}
            )
        except ValueError as e:
            logger.error(f"Platform initialization failed: {e}")
            sys.exit(1)

        # Load environment variables (only needed for local development)
        load_dotenv()

        # Validate environment variables (generic + platform-specific)
        ValidateEnvironmentVariables(platform)

        # Set up Google Cloud authentication
        setup_google_cloud_auth()

        # Initialize tracing
        enable_cloud_trace = os.getenv("ENABLE_CLOUD_TRACE", "true").lower() == "true"
        tracer = setup_tracing(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"), enable_cloud_trace=enable_cloud_trace
        )

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
