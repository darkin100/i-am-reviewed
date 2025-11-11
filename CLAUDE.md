# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PR Review Agent that uses Google's **Gemini 2.5 Flash** via Vertex AI to automatically review pull requests. The agent fetches PR data using GitHub CLI, analyzes the changes, and posts review comments.

Documentation for Google GenAI: https://google.github.io/adk-docs/

## Environment Setup

The project uses a Python virtual environment located at `venv/`.

**Activate the environment:**
```bash
source venv/bin/activate
```

**Required environment variables (in `pr_agent/.env`):**
```bash
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2

# GitHub
GITHUB_REPOSITORY=owner/repo  # e.g., "darkin100/i-am-reviewed"
GITHUB_PR_NUMBER=1
```

**Note:** GitHub CLI authentication is handled via `gh auth login` - no GITHUB_TOKEN needed if already authenticated.

## Architecture

### Core Components

**`pr_agent/github_tools.py`** - GitHub CLI wrapper functions:
- `get_pr_info(repo, pr_number)` - Fetches PR metadata using `gh pr view`
- `get_pr_diff(repo, pr_number)` - Gets the full diff using `gh pr diff`
- `post_pr_comment(repo, pr_number, body)` - Posts comment using `gh pr comment`

**`pr_agent/main.py`** - Main execution script:
- Loads environment variables
- Fetches PR data via GitHub CLI
- Creates a Gemini client and generates review
- Posts review comment back to PR

**`pr_agent/reviewer.py`** - (Legacy, not currently used)
- Originally defined ADK Agent configuration
- Current implementation uses `google.genai.Client` directly instead

### Technology Stack

- **Google GenAI (v1.47.0)** - Gemini model integration via Vertex AI
- **Google Cloud AI Platform (v1.123.0)** - Vertex AI backend
- **GitHub CLI** - For fetching PR data and posting comments
- **python-dotenv** - Environment variable management

## How to Run the PR Review Agent

1. **Configure environment variables** in `pr_agent/.env`:
   ```bash
   cp pr_agent/.env.example pr_agent/.env
   # Edit .env with your GCP project and target PR details
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth application-default login
   ```

3. **Authenticate with GitHub CLI** (if not already done):
   ```bash
   gh auth login
   ```

4. **Run the agent**:
   ```bash
   source venv/bin/activate
   python -m pr_agent.main
   ```

The agent will:
- Fetch PR metadata and diff from GitHub
- Send to Gemini 2.5 Flash for analysis
- Generate a structured review
- Post the review as a comment on the PR

## Implementation Details

The current implementation uses the **google.genai.Client** directly instead of the Google ADK Runner framework:

```python
from google import genai

# Create Vertex AI client
client = genai.Client(
    vertexai=True,
    project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION')
)

# Generate review
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
    config=genai.types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.7
    )
)
```

This approach is simpler for one-shot tasks like PR reviews compared to using the full ADK Runner with session management.

## Key Considerations

1. **Authentication**: Requires both GCP and GitHub authentication
   ```bash
   gcloud auth application-default login  # GCP
   gh auth login                          # GitHub
   ```

2. **GitHub CLI**: The agent uses `gh` CLI commands via subprocess
   - Ensure GitHub CLI is installed and authenticated
   - Check with: `gh auth status`

3. **Environment Variables**: All configuration is via `.env` file
   - See `pr_agent/.env.example` for template
   - `.env` is gitignored to protect credentials
