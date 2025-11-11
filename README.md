# PR Review Agent (MVP)

A simple PR review agent using Google ADK and Gemini 2.5 Flash to automatically review pull requests.

## Setup

### Prerequisites

1. **Python 3.11+** with virtual environment
2. **GitHub CLI (`gh`)** - Install from https://cli.github.com/
3. **Google Cloud SDK** - For Vertex AI authentication
4. **GitHub authentication** - Run `gh auth login`

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
   ```bash
   # Google Cloud / Vertex AI
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=europe-west2  # or your preferred region

   # GitHub - Update for the PR you want to review
   GITHUB_REPOSITORY=owner/repo        # e.g., "darkin100/i-am-reviewed"
   GITHUB_PR_NUMBER=1                  # PR number to review
   ```

3. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth application-default login
   ```

4. **Authenticate with GitHub CLI:**
   ```bash
   gh auth login
   ```

**Note**: GitHub token is handled automatically by `gh` CLI - no need to set `GITHUB_TOKEN` in `.env`.

## Usage

### Run the PR Review Agent

```bash
# Make sure you're in the project root and venv is activated
source venv/bin/activate

# Run the agent
python -m pr_agent.main
```

### Test with a Real PR

1. Find a public PR to test with (or create one in your own repo)
2. Update `.env` with the repository and PR number:
   ```bash
   GITHUB_REPOSITORY=facebook/react
   GITHUB_PR_NUMBER=28099
   ```
3. Run the agent:
   ```bash
   python -m pr_agent.main
   ```
4. Check the PR for the review comment

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

The agent uses a simple, direct approach for one-shot PR reviews:

- **`pr_agent/github_tools.py`** - GitHub CLI wrapper functions
  - `get_pr_info()` - Fetches PR metadata using `gh pr view`
  - `get_pr_diff()` - Gets diff using `gh pr diff`
  - `post_pr_comment()` - Posts comments using `gh pr comment`

- **`pr_agent/main.py`** - Main execution flow
  - Loads environment variables
  - Fetches PR data via GitHub CLI
  - Creates `google.genai.Client` for Vertex AI
  - Generates review using Gemini 2.5 Flash
  - Posts review comment back to PR

- **`pr_agent/reviewer.py`** - (Legacy, not currently used)
  - Originally for Google ADK Agent configuration
  - Current implementation uses genai Client directly for simplicity

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

## What's Working

✅ Fetch PR metadata and diff using GitHub CLI
✅ Analyze changes with Gemini 2.5 Flash
✅ Post review as a single PR comment
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

### GitHub CLI not authenticated
```bash
gh auth login
```

### Google Cloud not authenticated
```bash
gcloud auth application-default login
```

### Module import errors
```bash
# Make sure you're in the project root
cd /Users/glyndarkin/Work/pr-review-agent
source venv/bin/activate
python -m pr_agent.main
```

## Documentation

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## License

MIT