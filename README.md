# PR Review Agent (MVP)

A simple PR review agent using Google ADK and Gemini 2.5 Flash to automatically review pull requests.

## Setup

### Prerequisites

1. **Python 3.11+** with virtual environment
2. **GitHub CLI (`gh`)** - Already installed ✓
3. **Google Cloud credentials** - Already configured ✓
4. **GitHub authentication** - Already logged in ✓

### Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (already done)
pip install -r requirements.txt
```

### Configuration

Edit `pr_agent/.env` and set:

```bash
# Google Cloud (already set)
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=iamreleased
GOOGLE_CLOUD_LOCATION=europe-west2

# GitHub - Update these for your test PR
GITHUB_REPOSITORY=owner/repo        # e.g., "octocat/Hello-World"
GITHUB_PR_NUMBER=1                  # PR number to review
```

**Note**: `GITHUB_TOKEN` is optional since you're already authenticated with `gh auth login`.

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

- **`pr_agent/github_tools.py`** - GitHub CLI wrapper functions
- **`pr_agent/reviewer.py`** - Agent configuration with review instructions
- **`pr_agent/main.py`** - Main execution flow

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