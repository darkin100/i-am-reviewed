"""Main execution script for PR review agent."""

import os
import sys
import subprocess
import argparse
import tempfile
from dotenv import load_dotenv
from google import genai

from pr_agent.platforms import get_platform


def setup_google_cloud_auth():


    # Check if credentials JSON is provided via environment variable (CI/CD)
    credentials_json = os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON')
    if not credentials_json:
        # No credentials provided - may rely on other auth methods
        print("Warning: No GOOGLE_CLOUD_CREDENTIALS_JSON found. Attempting to use default credentials.")
        return

    # Write credentials to a temporary file
    try:
        # Create a temporary file that won't be automatically deleted
        fd, credentials_path = tempfile.mkstemp(suffix='.json', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(credentials_json)

        # Set the environment variable
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        print(f"Google Cloud credentials configured at: {credentials_path}")
    except Exception as e:
        print(f"Error setting up credentials: {e}")
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
        print("Error: Could not determine PR/MR number from environment variables")
        print(f"Set one of: PR_NUMBER")
        sys.exit(1)

    try:
        return int(pr_number_str)
    except ValueError:
        print(f"Error: PR/MR number must be an integer, got: {pr_number_str}")
        sys.exit(1)


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
  python -m pr_agent.main --provider github

  # Review GitLab MR
  python -m pr_agent.main --provider gitlab

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


def main():
    """Run PR review workflow."""
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Load environment variables (only needed for local development)
        load_dotenv()

        # Set up Google Cloud authentication
        setup_google_cloud_auth()

        # Get platform implementation
        try:
            platform = get_platform(args.provider)
            platform_name = args.provider.lower()
            print(f"Using platform: {platform.get_platform_name()}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Set up platform authentication
        platform.setup_auth()

        # Get repository identifier
        repo = get_repository_identifier()
        print(f"Repository: {repo}")

        # Get PR/MR number
        pr_number = get_pr_number()
        print(f"Starting review for PR/MR #{pr_number} in {repo}...")

        # Fetch PR/MR data using platform abstraction
        print("Fetching PR/MR metadata...")
        pr_info = platform.get_pr_info(repo, pr_number)

        print("Fetching PR/MR diff...")
        pr_diff = platform.get_pr_diff(repo, pr_number)

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

        # Get agent review using genai client directly
        print("Generating review with AI...")
        client = genai.Client(
            vertexai=True,
            project=os.getenv('GOOGLE_CLOUD_PROJECT'),
            location=os.getenv('GOOGLE_CLOUD_LOCATION')
        )

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

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )

        review_text = response.text

        if not review_text:
            print("Error: No response from model")
            sys.exit(1)

        # Post review comment using platform abstraction
        print("Posting review comment to PR/MR...")
        platform.post_pr_comment(repo, pr_number, review_text)

        print(f"✓ Review successfully posted to PR/MR #{pr_number}")

        # Generate platform-specific URL
        # TODO: Refactor this into the Gitlab/GitHub platform classes
        if platform_name == 'github':
            print(f"View at: https://github.com/{repo}/pull/{pr_number}")
        elif platform_name == 'gitlab':
            # GitLab URL structure: https://gitlab.com/group/project/-/merge_requests/{iid}
            gitlab_host = os.getenv('CI_SERVER_HOST', 'gitlab.com')
            print(f"View at: https://{gitlab_host}/{repo}/-/merge_requests/{pr_number}")

    except subprocess.CalledProcessError as e:
        print(f"Error: CLI command failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
