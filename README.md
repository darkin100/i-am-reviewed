# PR Review Agent (MVP)

A multi-platform PR review agent using Google ADK and Gemini 2.5 Flash to automatically review pull requests and merge requests.

Supports both **GitHub** and **GitLab** through a platform-agnostic architecture.

## Setup

### Prerequisites

1. **Python 3.11+** with virtual environment
2. **Git hosting CLI** (choose based on your platform):
   - **GitHub CLI (`gh`)** - Install from https://cli.github.com/
   - **GitLab CLI (`glab`)** - Install from https://gitlab.com/gitlab-org/cli
3. **Google Cloud SDK** - For Vertex AI authentication
4. **Git platform authentication**:
   - GitHub: Run `gh auth login`
   - GitLab: Run `glab auth login`

### Installation

```bash
# Clone the repository
git clone https://github.com/darkin100/i-am-reviewed.git
cd i-am-reviewed

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Copy the example environment file:**
   ```bash
   cp pr_agent/.env.example pr_agent/.env
   ```

2. **Edit `pr_agent/.env` with your settings:**

   For **GitHub**:
   ```bash
   # Google Cloud / Vertex AI
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=europe-west2  # or your preferred region

   # GitHub - Update for the PR you want to review
   GITHUB_REPOSITORY=owner/repo        # e.g., "darkin100/i-am-reviewed"
   GITHUB_PR_NUMBER=1                  # PR number to review
   ```

   For **GitLab**:
   ```bash
   # Google Cloud / Vertex AI
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=europe-west2  # or your preferred region

   # GitLab - Update for the MR you want to review
   CI_PROJECT_PATH=group/project       # e.g., "mygroup/myproject"
   CI_MERGE_REQUEST_IID=1              # MR IID to review
   ```

   **Or use generic variables** (works for both platforms):
   ```bash
   REPOSITORY=owner/repo           # Repository identifier
   PR_NUMBER=1                     # PR/MR number
   ```

3. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth application-default login
   ```

4. **Authenticate with your Git platform:**
   - GitHub: `gh auth login`
   - GitLab: `glab auth login`

**Note**: Authentication tokens are handled automatically by CLI tools - no need to set tokens in `.env`.

## Usage

### Run the PR Review Agent

```bash
# Make sure you're in the project root and venv is activated
source venv/bin/activate

# Run for GitHub
python -m pr_agent.main --provider github

# Or run for GitLab
python -m pr_agent.main --provider gitlab
```

### Test with a Real PR/MR

**For GitHub:**
1. Find a public PR to test with (or create one in your own repo)
2. Update `.env` with the repository and PR number:
   ```bash
   GITHUB_REPOSITORY=facebook/react
   GITHUB_PR_NUMBER=28099
   ```
3. Run the agent:
   ```bash
   python -m pr_agent.main --provider github
   ```
4. Check the PR for the review comment

**For GitLab:**
1. Find a public MR to test with (or create one in your own project)
2. Update `.env` with the project path and MR IID:
   ```bash
   CI_PROJECT_PATH=gitlab-org/gitlab
   CI_MERGE_REQUEST_IID=100
   ```
3. Run the agent:
   ```bash
   python -m pr_agent.main --provider gitlab
   ```
4. Check the MR for the review comment

### Example Output

```
Starting review for PR #123 in owner/repo...
Fetching PR metadata...
Fetching PR diff...
Generating review with AI agent...
Posting review comment to PR...
✓ Review successfully posted to PR #123
View at: https://github.com/owner/repo/pull/123
```

## Architecture

The agent uses a **platform-agnostic architecture** with pluggable Git hosting providers:

### Platform Abstraction Layer

- **`pr_agent/platforms/base.py`** - Abstract base class defining the platform interface
  - `get_pr_info()` - Fetch PR/MR metadata
  - `get_pr_diff()` - Get diff of changes
  - `post_pr_comment()` - Post review comments
  - `get_pr_number_from_event()` - Extract PR/MR number from CI/CD context

- **`pr_agent/platforms/github.py`** - GitHub implementation using `gh` CLI
  - Uses GitHub CLI commands (`gh pr view`, `gh pr diff`, `gh pr comment`)
  - Supports GitHub Actions environment variables

- **`pr_agent/platforms/gitlab.py`** - GitLab implementation using `glab` CLI
  - Uses GitLab CLI commands (`glab mr view`, `glab mr diff`, `glab mr note`)
  - Supports GitLab CI environment variables

- **`pr_agent/platforms/__init__.py`** - Factory function for platform instantiation
  - `get_platform(provider)` - Returns appropriate platform implementation

### Main Application

- **`pr_agent/main.py`** - Platform-agnostic main execution flow
  - Parses command-line arguments (`--provider`)
  - Loads platform implementation via factory
  - Fetches PR/MR data through platform abstraction
  - Creates `google.genai.Client` for Vertex AI
  - Generates review using Gemini 2.5 Flash
  - Posts review comment back through platform abstraction

- **`pr_agent/reviewer.py`** - (Legacy, not currently used)
  - Originally for Google ADK Agent configuration
  - Current implementation uses genai Client directly for simplicity

### Extensibility

The abstract base class design makes it easy to add support for additional platforms (Bitbucket, Azure DevOps, etc.) by implementing the `GitPlatform` interface.

## Implementation Approach

This MVP uses `google.genai.Client` directly rather than the full Google ADK Runner framework:

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

**Why this approach?**
- Simpler for one-shot tasks like PR reviews
- No session management or runner complexity needed
- Direct model invocation is faster to implement
- Can upgrade to full ADK framework later if needed for multi-turn conversations or complex workflows

## CI/CD Integration

The agent can be deployed as a GitHub Action or GitLab CI job to automatically review PRs/MRs.

### GitHub Actions

See [docs/example-github-actions.yml](docs/example-github-actions.yml) for a complete example.

**Quick setup:**

1. Copy the example workflow to `.github/workflows/review-pr.yml`
2. Set up repository secrets:
   - `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
   - `GOOGLE_CLOUD_LOCATION`: GCP region (e.g., `europe-west2`)
   - `GOOGLE_CLOUD_CREDENTIALS`: Your GCP service account JSON
3. The workflow automatically uses `secrets.GITHUB_TOKEN` for GitHub API access

**Usage in workflow:**

```yaml
steps:
  - uses: darkin100/i-am-reviewed@v1.0
    with:
      github-token: ${{ secrets.GITHUB_TOKEN }}
      pr-number: ${{ github.event.pull_request.number }}
      google-cloud-project: ${{ secrets.GOOGLE_CLOUD_PROJECT }}
      google-cloud-location: ${{ secrets.GOOGLE_CLOUD_LOCATION }}
      google-cloud-credentials: ${{ secrets.GOOGLE_CLOUD_CREDENTIALS }}
```

### GitLab CI

See [docs/example-gitlab-ci.yml](docs/example-gitlab-ci.yml) for a complete example.

**Quick setup:**

1. Copy the example workflow to `.gitlab-ci.yml` in your repository root
2. Set up CI/CD variables in your GitLab project (Settings > CI/CD > Variables):
   - `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
   - `GOOGLE_CLOUD_LOCATION`: GCP region (e.g., `europe-west2`)
   - `GOOGLE_CLOUD_CREDENTIALS`: Your GCP service account JSON (as File type)
3. The pipeline automatically uses `CI_JOB_TOKEN` for GitLab API access (no additional token required)

**Usage in .gitlab-ci.yml:**

```yaml
review_merge_request:
  stage: review
  image: europe-west2-docker.pkg.dev/iamreleased/docker-images/pr-review-agent-gitlab:latest
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  variables:
    GOOGLE_CLOUD_PROJECT: $GOOGLE_CLOUD_PROJECT
    GOOGLE_CLOUD_LOCATION: $GOOGLE_CLOUD_LOCATION
    GOOGLE_CLOUD_CREDENTIALS_JSON: $GOOGLE_CLOUD_CREDENTIALS
    GITLAB_TOKEN: $CI_JOB_TOKEN
```

**Important for GitLab:**
- The `GITLAB_TOKEN` environment variable is required for the `glab` CLI to authenticate
- Use `CI_JOB_TOKEN` (automatically provided by GitLab CI) or a project/personal access token
- The `CI_JOB_TOKEN` has permissions to read MR data and post comments automatically

## What's Working

✅ Multi-platform support (GitHub and GitLab)
✅ Platform-agnostic architecture with abstract base class
✅ Fetch PR/MR metadata and diff using platform CLI tools
✅ Analyze changes with Gemini 2.5 Flash
✅ Post review as a single PR/MR comment
✅ CI/CD integration (GitHub Actions and GitLab CI)
✅ Basic error handling

## Post-MVP Enhancements

Future improvements (not in MVP):
- Inline comments on specific lines
- Severity classification
- Docker containerization
- GitHub Actions integration
- File-by-file review for large PRs
- Configurable review rules

## Troubleshooting

### Git Platform CLI not authenticated

**GitHub:**
```bash
gh auth login
```

**GitLab:**
```bash
glab auth login
```

### GitLab 401 Unauthorized Error in CI/CD

If you see `401 Unauthorized` when running in GitLab CI:

```
Error: CLI command failed: Command '['glab', 'mr', 'diff', '9', '-R', 'repo/name']' returned non-zero exit status 1.
stderr: ERROR Could not find merge request diffs: GET https://gitlab.com/api/v4/...: 401 {message: 401 Unauthorized}
```

**Solution:** Ensure `GITLAB_TOKEN` is set in your CI/CD pipeline:

```yaml
variables:
  GITLAB_TOKEN: $CI_JOB_TOKEN  # Use GitLab's automatic job token
```

The `CI_JOB_TOKEN` is automatically provided by GitLab CI and has the necessary permissions to:
- Read merge request data
- Post comments on merge requests

**Alternative:** If `CI_JOB_TOKEN` doesn't work, create a project or personal access token with `api` scope and add it as a CI/CD variable named `GITLAB_TOKEN`.

### Google Cloud not authenticated
```bash
gcloud auth application-default login
```

### Module import errors
```bash
# Make sure you're in the project root
cd /Users/glyndarkin/Work/pr-review-agent
source venv/bin/activate
python -m pr_agent.main --provider github  # or --provider gitlab
```

### Provider argument missing
```bash
# ERROR: the following arguments are required: --provider
# Solution: Always specify --provider flag
python -m pr_agent.main --provider github
```

## Documentation

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)


## License

MIT