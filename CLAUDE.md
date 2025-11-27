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

**Required environment variables (in `agent/.env`):**

For **GitHub**:
```bash
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2

# GitHub (using generic variables)
REPOSITORY=owner/repo           # e.g., "darkin100/i-am-reviewed"
PR_NUMBER=1                     # PR number to review
GH_TOKEN=ghp_xxxxxxxxxxxx       # GitHub Personal Access Token

# Optional: Google Cloud credentials for CI/CD
# GOOGLE_CLOUD_CREDENTIALS=<service-account-json>
```

For **GitLab**:
```bash
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2

# GitLab (using generic variables)
REPOSITORY=group/project        # e.g., "mygroup/myproject"
PR_NUMBER=1                     # MR IID to review
GITLAB_TOKEN=glpat-xxxxxxxxxxxx # GitLab Personal Access Token
CI_SERVER_HOST=gitlab.com       # Optional: custom GitLab instance

# Optional: Google Cloud credentials for CI/CD
# GOOGLE_CLOUD_CREDENTIALS=<service-account-json>
```

**Note:**
- `GH_TOKEN` is required for GitHub (use Personal Access Token with `repo` scope)
- `GITLAB_TOKEN` is required for GitLab (use Personal Access Token with `api` scope)
- In CI/CD, these tokens may be automatically provided (`GITHUB_TOKEN`, `CI_JOB_TOKEN`)

## Architecture

### Platform Abstraction Layer

**`agent/platforms/base.py`** - Abstract base class (`GitPlatform`):
- Defines the interface all platform implementations must follow
- `get_pr_info(repo, pr_number)` - Fetch PR/MR metadata
- `get_pr_diff(repo, pr_number)` - Get full diff
- `post_pr_comment(repo, pr_number, body)` - Post review comment

**`agent/platforms/github.py`** - GitHub implementation (`GitHubPlatform`):
- Uses `gh` CLI commands (`gh pr view`, `gh pr diff`, `gh pr comment`)
- Extracts PR number from `GITHUB_EVENT_PATH` in GitHub Actions

**`agent/platforms/gitlab.py`** - GitLab implementation (`GitLabPlatform`):
- Uses `glab` CLI commands (`glab mr view`, `glab mr diff`, `glab mr note`)
- Extracts MR IID from `CI_MERGE_REQUEST_IID` in GitLab CI
- Normalizes GitLab MR data to match GitHub's structure

**`agent/platforms/__init__.py`** - Platform factory:
- `get_platform(provider)` - Returns the appropriate platform instance

### Main Application

**`agent/main.py`** - Platform-agnostic main execution script:
- Parses command-line arguments (`--provider github` or `--provider gitlab`)
- Uses platform factory to get appropriate implementation
- Fetches PR/MR data through platform abstraction
- Creates Gemini client and generates review
- Posts review comment through platform abstraction

**`agent/reviewer.py`** - (Legacy, not currently used)
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

1. **Configure environment variables** in `agent/.env`:
   ```bash
   cp agent/.env.example agent/.env
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
   python -m agent.main --provider github

   # For GitLab
   python -m agent.main --provider gitlab
   ```

The agent will:
- Fetch PR/MR metadata and diff from the specified platform
- Send to Gemini 2.5 Flash for analysis
- Generate a structured review
- Post the review as a comment on the PR/MR

## Implementation Details

The current implementation uses **Google ADK** with `LlmAgent` and `InMemoryRunner`:

```python
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner

# Create the agent
agent = LlmAgent(
    model='gemini-2.5-flash',
    name='pr_review_agent',
    instruction=system_instruction,
    generate_content_config=types.GenerateContentConfig(temperature=0.7)
)

# Run with InMemoryRunner
runner = InMemoryRunner(agent=agent, app_name='pr_review')
events = await runner.run_debug(prompt)
```

This approach provides async execution with event-based response handling.

## Key Considerations

1. **Authentication**: Requires both GCP and Git platform authentication
   ```bash
   gcloud auth application-default login  # GCP
   # Set GH_TOKEN or GITLAB_TOKEN in .env file
   ```

2. **Platform CLI Tools**: The agent uses CLI commands via subprocess
   - **GitHub**: Uses `gh` CLI - requires `GH_TOKEN` environment variable
   - **GitLab**: Uses `glab` CLI - requires `GITLAB_TOKEN` environment variable
   - Ensure the appropriate CLI tool is installed

3. **Command-line Arguments**: The `--provider` flag is required
   - Always specify either `--provider github` or `--provider gitlab`
   - This determines which platform implementation to use

4. **Environment Variables**: All configuration is via `.env` file
   - See `agent/.env.example` for template
   - `.env` is gitignored to protect credentials
   - **Required variables**:
     - `REPOSITORY` (or `GITHUB_REPOSITORY`/`CI_PROJECT_PATH`)
     - `PR_NUMBER` (or `GITHUB_PR_NUMBER`/`CI_MERGE_REQUEST_IID`)
     - `GH_TOKEN` (for GitHub) or `GITLAB_TOKEN` (for GitLab)
     - `GOOGLE_CLOUD_PROJECT`
     - `GOOGLE_CLOUD_LOCATION`

5. **Docker Images**: Two separate Docker images are built:
   - `Dockerfile.Github` - Includes `gh` CLI, sets `--provider github`
   - `Dockerfile.Gitlab` - Includes `glab` CLI, sets `--provider gitlab`

## Tracing and Observability

The agent includes **Cloud Trace** integration via OpenTelemetry for distributed tracing.

### Configuration

Set in `agent/.env`:
```bash
ENABLE_CLOUD_TRACE=true   # Set to 'false' for console output (local debugging)
```

### Trace Structure

```
pr_review_workflow (root span)
├── github.get_pr_info / gitlab.get_pr_info
├── github.get_pr_diff / gitlab.get_pr_diff
├── llm_agent_execution
│   └── [ADK automatic spans: invocation, agent_run, call_llm]
└── github.post_pr_comment / gitlab.post_pr_comment
```

### Key Files

- **`agent/tracing_config.py`** - Tracing setup and helpers:
  - `setup_tracing(project_id, enable_cloud_trace)` - Initialize OpenTelemetry
  - `get_tracer()` - Get global tracer instance
  - `@traced(span_name)` - Decorator for method instrumentation
  - `custom_span(name, attributes)` - Context manager for ad-hoc spans

### Adding Custom Spans

```python
from agent.tracing_config import custom_span

with custom_span("my_operation", {"key": "value"}):
    # Your code here
    pass
```

### Log Correlation

Logs automatically include `trace_id` and `span_id` when running within a span:
```json
{
  "timestamp": "2025-01-27T10:30:00Z",
  "level": "INFO",
  "message": "Fetching PR metadata",
  "trace_id": "abc123...",
  "span_id": "def456..."
}
```

Click trace IDs in Cloud Logging to jump directly to Cloud Trace.

### Viewing Traces

Access traces in the GCP Console:
```
https://console.cloud.google.com/traces/list?project={GOOGLE_CLOUD_PROJECT}
```

## External Documentation

GitLab documentation used

   https://docs.gitlab.com/topics/build_your_application/