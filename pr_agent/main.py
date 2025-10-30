"""Main execution script for PR review agent."""

import os
import sys
import subprocess
from dotenv import load_dotenv

from pr_agent.github_tools import get_pr_info, get_pr_diff, post_pr_comment
from pr_agent.reviewer import create_review_agent


def main():
    """Run PR review workflow."""
    try:
        # Load environment variables
        load_dotenv()

        # Get required environment variables
        repo = os.getenv('GITHUB_REPOSITORY')
        pr_number_str = os.getenv('GITHUB_PR_NUMBER')

        if not repo:
            print("Error: GITHUB_REPOSITORY environment variable not set")
            sys.exit(1)

        if not pr_number_str:
            print("Error: GITHUB_PR_NUMBER environment variable not set")
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

        # Get agent review
        print("Generating review with AI agent...")
        agent = create_review_agent()
        response = agent.generate(prompt)
        review_text = response.text

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
