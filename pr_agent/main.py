"""Main execution script for PR review agent."""

import os
import sys
import subprocess
import json
import tempfile
from dotenv import load_dotenv
from google import genai

from pr_agent.github_tools import get_pr_info, get_pr_diff, post_pr_comment


def get_pr_number_from_event():
    """Extract PR number from GitHub Actions event context."""
    event_path = os.getenv('GITHUB_EVENT_PATH')
    if not event_path:
        return None

    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            # Extract PR number from the event
            if 'pull_request' in event_data:
                return event_data['pull_request']['number']
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not extract PR number from event: {e}")

    return None


def setup_google_cloud_auth():
    """Set up Google Cloud authentication for GitHub Actions."""
    # If GOOGLE_APPLICATION_CREDENTIALS is already set, use it (local dev)
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("Using existing GOOGLE_APPLICATION_CREDENTIALS")
        return

    # Check if credentials JSON is provided via environment variable (GitHub Actions)
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


def main():
    """Run PR review workflow."""
    try:
        # Load environment variables (only needed for local development)
        load_dotenv()

        # Set up Google Cloud authentication
        setup_google_cloud_auth()

        # Check if running in GitHub Actions
        is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'

        # Get required environment variables
        repo = os.getenv('GITHUB_REPOSITORY')
        pr_number_str = os.getenv('GITHUB_PR_NUMBER')

        # If running in GitHub Actions and PR number not explicitly set, extract from event
        if is_github_actions and not pr_number_str:
            pr_number_from_event = get_pr_number_from_event()
            if pr_number_from_event:
                pr_number_str = str(pr_number_from_event)
                print(f"Detected PR number from GitHub event: {pr_number_str}")

        if not repo:
            print("Error: GITHUB_REPOSITORY environment variable not set")
            sys.exit(1)

        if not pr_number_str:
            print("Error: GITHUB_PR_NUMBER environment variable not set")
            print("In GitHub Actions, this should be automatically extracted from the event context.")
            sys.exit(1)

        try:
            pr_number = int(pr_number_str)
        except ValueError:
            print(f"Error: GITHUB_PR_NUMBER must be an integer, got: {pr_number_str}")
            sys.exit(1)

        print(f"Starting review for PR #{pr_number} in {repo}...")

        # Fetch PR data
        print("Fetching PR metadata...")
        pr_info = get_pr_info(repo, pr_number)

        print("Fetching PR diff...")
        pr_diff = get_pr_diff(repo, pr_number)

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

        # Post review comment
        print("Posting review comment to PR...")
        post_pr_comment(repo, pr_number, review_text)

        print(f"✓ Review successfully posted to PR #{pr_number}")
        print(f"View at: https://github.com/{repo}/pull/{pr_number}")

    except subprocess.CalledProcessError as e:
        print(f"Error: GitHub CLI command failed: {e}")
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
