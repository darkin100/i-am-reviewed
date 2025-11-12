# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **multi-platform** Code Review Agent that uses Google's **Gemini 2.5 Flash** via Vertex AI to automatically review pull requests and merge requests.

**Supported Platforms:**
- GitHub (using `gh` CLI)
- GitLab (using `glab` CLI)

The agent uses a **platform-agnostic architecture** with an abstract base class that allows easy extension to other Git hosting providers (Bitbucket, Azure DevOps, etc.).

Documentation for Google GenAI: https://google.github.io/adk-docs/

## Environment Setup

The project uses a Python virtual environment located at `venv/`.

**Activate the environment:**
```bash
source venv/bin/activate
```

**Required environment variables (in `pr_agent/.env`):**

For **GitHub**:
```bash
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2

# GitHub
GITHUB_REPOSITORY=owner/repo  # e.g., "darkin100/i-am-reviewed"
GITHUB_PR_NUMBER=1
```

For **GitLab**:
```bash
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2

# GitLab
CI_PROJECT_PATH=group/project  # e.g., "mygroup/myproject"
CI_MERGE_REQUEST_IID=1
```

**Or use generic variables** (works for both):
```bash
GIT_REPOSITORY=owner/repo
GIT_PR_NUMBER=1
```

**Note:** CLI authentication is handled via `gh auth login` (GitHub) or `glab auth login` (GitLab) - no tokens needed in `.env` if already authenticated.

## Architecture

### Platform Abstraction Layer

**`pr_agent/platforms/base.py`** - Abstract base class (`GitPlatform`):
- Defines the interface all platform implementations must follow
- `get_pr_info(repo, pr_number)` - Fetch PR/MR metadata
- `get_pr_diff(repo, pr_number)` - Get full diff
- `post_pr_comment(repo, pr_number, body)` - Post review comment
- `get_pr_number_from_event()` - Extract PR/MR number from CI/CD context

**`pr_agent/platforms/github.py`** - GitHub implementation (`GitHubPlatform`):
- Uses `gh` CLI commands (`gh pr view`, `gh pr diff`, `gh pr comment`)
- Extracts PR number from `GITHUB_EVENT_PATH` in GitHub Actions

**`pr_agent/platforms/gitlab.py`** - GitLab implementation (`GitLabPlatform`):
- Uses `glab` CLI commands (`glab mr view`, `glab mr diff`, `glab mr note`)
- Extracts MR IID from `CI_MERGE_REQUEST_IID` in GitLab CI
- Normalizes GitLab MR data to match GitHub's structure

**`pr_agent/platforms/__init__.py`** - Platform factory:
- `get_platform(provider)` - Returns the appropriate platform instance

### Main Application

**`pr_agent/main.py`** - Platform-agnostic main execution script:
- Parses command-line arguments (`--provider github` or `--provider gitlab`)
- Uses platform factory to get appropriate implementation
- Fetches PR/MR data through platform abstraction
- Creates Gemini client and generates review
- Posts review comment through platform abstraction

**`pr_agent/reviewer.py`** - (Legacy, not currently used)
- Originally defined ADK Agent configuration
- Current implementation uses `google.genai.Client` directly instead

### Technology Stack

- **Google GenAI (v1.47.0)** - Gemini model integration via Vertex AI
- **Google Cloud AI Platform (v1.123.0)** - Vertex AI backend
- **GitHub CLI (`gh`)** - For fetching GitHub PR data and posting comments
- **GitLab CLI (`glab`)** - For fetching GitLab MR data and posting comments
- **python-dotenv** - Environment variable management
- **Abstract Base Classes** - For platform abstraction

## How to Run the PR Review Agent

1. **Configure environment variables** in `pr_agent/.env`:
   ```bash
   cp pr_agent/.env.example pr_agent/.env
   # Edit .env with your GCP project and target PR/MR details
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth application-default login
   ```

3. **Authenticate with your Git platform CLI**:
   - GitHub: `gh auth login`
   - GitLab: `glab auth login`

4. **Run the agent** (specify platform with `--provider` flag):
   ```bash
   source venv/bin/activate

   # For GitHub
   python -m pr_agent.main --provider github

   # For GitLab
   python -m pr_agent.main --provider gitlab
   ```

The agent will:
- Fetch PR/MR metadata and diff from the specified platform
- Send to Gemini 2.5 Flash for analysis
- Generate a structured review
- Post the review as a comment on the PR/MR

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

1. **Authentication**: Requires both GCP and Git platform authentication
   ```bash
   gcloud auth application-default login  # GCP
   gh auth login                          # GitHub
   glab auth login                        # GitLab
   ```

2. **Platform CLI Tools**: The agent uses CLI commands via subprocess
   - **GitHub**: Uses `gh` CLI - check with `gh auth status`
   - **GitLab**: Uses `glab` CLI - check with `glab auth status`
   - Ensure the appropriate CLI tool is installed and authenticated

3. **Command-line Arguments**: The `--provider` flag is required
   - Always specify either `--provider github` or `--provider gitlab`
   - This determines which platform implementation to use

4. **Environment Variables**: All configuration is via `.env` file
   - See `pr_agent/.env.example` for template
   - `.env` is gitignored to protect credentials
   - Use platform-specific or generic variable names

5. **Docker Images**: Two separate Docker images are built:
   - `Dockerfile.Github` - Includes `gh` CLI, sets `--provider github`
   - `Dockerfile.Gitlab` - Includes `glab` CLI, sets `--provider gitlab`
