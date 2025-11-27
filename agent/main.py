"""Main execution script for PR review agent."""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent.logging_config import setup_logging, get_logger
from agent.platforms import get_platform
from agent.tracing_config import setup_tracing, get_tracer
from agent.utils import strip_markdown_wrapper

# Initialize logging first
setup_logging()
logger = get_logger(__name__)


def setup_google_cloud_auth():


    # Check if credentials JSON is provided via environment variable (CI/CD)
    credentials_json = os.getenv('GOOGLE_CLOUD_CREDENTIALS')
    if not credentials_json:
        # No credentials provided - may rely on other auth methods
        logger.warning("No GOOGLE_CLOUD_CREDENTIALS found, attempting to use default credentials")
        return

    # Write credentials to a temporary file
    try:
        # Create a temporary file that won't be automatically deleted
        fd, credentials_path = tempfile.mkstemp(suffix='.json', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(credentials_json)

        # Set the environment variable
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        logger.info("Google Cloud credentials configured", extra={"context": {"credentials_path": credentials_path}})
    except Exception as e:
        logger.error("Error setting up credentials", exc_info=True)
        raise


def get_repository_identifier() -> str:
    """Get repository identifier from environment variables.

    Tries generic REPOSITORY first, then falls back to platform-specific variables.

    Returns:
        Repository identifier (e.g., 'owner/repo' or 'group/project')

    Raises:
        SystemExit: If repository identifier cannot be determined
    """
    # Try generic variable first
    repo = os.getenv('REPOSITORY')
    if repo:
        return repo


def get_pr_number() -> int:
    """Get PR/MR number from environment variables or CI/CD context.

    Tries generic PR_NUMBER first, then platform-specific variables,
    and finally attempts to extract from CI/CD event context.

    Args:
        platform: Platform instance to use for event extraction
        platform_name: Name of the platform ('github' or 'gitlab')

    Returns:
        PR/MR number

    Raises:
        SystemExit: If PR number cannot be determined
    """
    # Try generic variable first
    pr_number_str = os.getenv('PR_NUMBER')


    # Validate and convert to integer
    if not pr_number_str:
        logger.error("Could not determine PR/MR number from environment variables. Set PR_NUMBER")
        sys.exit(1)

    try:
        return int(pr_number_str)
    except ValueError:
        logger.error("PR/MR number must be an integer", extra={"context": {"received_value": pr_number_str}})
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
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        missing_vars.append('GOOGLE_CLOUD_PROJECT')

    if not os.getenv('GOOGLE_CLOUD_LOCATION'):
        missing_vars.append('GOOGLE_CLOUD_LOCATION')

    if not os.getenv('GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY'):
        os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "true"

    if not os.getenv('OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT'):
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"

    # Enable Vertex AI backend for ADK
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

    # Validate generic environment variables
    if not os.getenv('REPOSITORY'):
        missing_vars.append('REPOSITORY (or platform-specific equivalent)')
    if not os.getenv('PR_NUMBER'):
        missing_vars.append('PR_NUMBER (or platform-specific equivalent)')


    # If platform is provided, validate platform-specific variables
    if platform:
        platform_missing = platform.validate_environment_variables()
        if platform_missing:
            missing_vars.extend(platform_missing)

    # Report all missing variables
    if missing_vars:
        logger.error("Missing required environment variables", extra={"context": {"missing_vars": missing_vars}})
        sys.exit(1)

    logger.info("Environment variables validated successfully")


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='AI-powered Pull/Merge Request Review Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review GitHub PR
  python -m agent.main --provider github

  # Review GitLab MR
  python -m agent.main --provider gitlab

Environment Variables:
  REPOSITORY
  PR_NUMBER
  GOOGLE_CLOUD_PROJECT - Google Cloud project ID
  GOOGLE_CLOUD_LOCATION - Google Cloud location (e.g., europe-west2)
        """
    )

    parser.add_argument(
        '--provider',
        type=str,
        required=True,
        choices=['github', 'gitlab'],
        help='Git hosting provider (github or gitlab)'
    )

    return parser.parse_args()


def create_review_agent() -> LlmAgent:
    """Create and configure the PR review agent.

    Returns:
        Configured LlmAgent for PR reviews
    """
    system_instruction = """You are a code reviewer analyzing a pull request.

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
Format your response in markdown for GitHub."""

    return LlmAgent(
        model='gemini-2.5-flash',
        name='pr_review_agent',
        description='An AI agent that reviews pull requests for code quality, bugs, and best practices.',
        instruction=system_instruction,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.7
        )
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
        runner = InMemoryRunner(agent=agent, app_name='pr_review')

        events = await runner.run_debug(prompt)

        # Extract text from the last event's content
        # run_debug() returns a list of Event objects
        for event in reversed(events):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        span.set_attribute("response_length", len(part.text))
                        return part.text

        return None


def main():
    """Run PR review workflow."""
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Get platform implementation
        try:
            platform = get_platform(args.provider)
            logger.info("Platform selected", extra={"context": {"platform": platform.get_platform_name()}})
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
        enable_cloud_trace = os.getenv('ENABLE_CLOUD_TRACE', 'true').lower() == 'true'
        tracer = setup_tracing(
            project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
            enable_cloud_trace=enable_cloud_trace
        )

        # Set up platform authentication
        platform.setup_auth()

        # Get repository identifier
        repo = get_repository_identifier()
        logger.info("Repository identified", extra={"context": {"repository": repo}})

        # Get PR/MR number
        pr_number = get_pr_number()
        logger.info("Starting PR review", extra={"context": {"repository": repo, "pr_number": pr_number}})

        # Start the main workflow span
        with tracer.start_as_current_span("pr_review_workflow") as root_span:
            root_span.set_attribute("repository", repo)
            root_span.set_attribute("pr_number", pr_number)
            root_span.set_attribute("platform", platform.get_platform_name())

            # Fetch PR/MR data using platform abstraction
            logger.info("Fetching PR/MR metadata")
            pr_info = platform.get_pr_info(repo, pr_number)
            logger.debug("PR metadata fetched", extra={"context": {"pr_info": pr_info}})

            logger.info("Fetching PR/MR diff")
            pr_diff = platform.get_pr_diff(repo, pr_number)
            logger.debug("Full PR diff", extra={"context": {"diff_length": len(pr_diff), "diff": pr_diff}})

            # Create review prompt
            prompt = f"""Review this pull request:

Title: {pr_info.get('title', 'N/A')}

Description:
{pr_info.get('body', 'No description provided')}

Branch: {pr_info.get('headRefName', 'N/A')} -> {pr_info.get('baseRefName', 'N/A')}

Author: {pr_info.get('author', {}).get('login', 'N/A')}

Changes:
{pr_diff}

Provide your code review."""

            # Get agent review using ADK Agent
            logger.info("Generating review with AI")
            logger.debug("LLM prompt", extra={"context": {"prompt": prompt}})
            review_text = asyncio.run(run_review_agent(prompt))

            if not review_text:
                logger.error("No response received from model")
                sys.exit(1)

            logger.debug("LLM response received", extra={"context": {"response_length": len(review_text), "review_text": review_text}})

            # Clean up any markdown code block wrappers that the AI might have added
            review_text = strip_markdown_wrapper(review_text)

            # Post review comment using platform abstraction
            logger.info("Posting review comment to PR/MR")
            logger.debug("Generated review content", extra={"context": {"review_text": review_text}})
            platform.post_pr_comment(repo, pr_number, review_text)

            logger.info("Review successfully posted", extra={"context": {"pr_number": pr_number}})

            # Generate platform-specific URL
            # TODO: Refactor this into the Gitlab/GitHub platform classes
            if platform.get_platform_name() == 'github':
                logger.info("Review URL", extra={"context": {"url": f"https://github.com/{repo}/pull/{pr_number}"}})
            elif platform.get_platform_name() == 'gitlab':
                # GitLab URL structure: https://gitlab.com/group/project/-/merge_requests/{iid}
                gitlab_host = os.getenv('CI_SERVER_HOST', 'gitlab.com')
                logger.info("Review URL", extra={"context": {"url": f"https://{gitlab_host}/{repo}/-/merge_requests/{pr_number}"}})

    except subprocess.CalledProcessError as e:
        logger.error("CLI command failed", extra={"context": {"error": str(e), "stdout": e.stdout, "stderr": e.stderr}}, exc_info=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
