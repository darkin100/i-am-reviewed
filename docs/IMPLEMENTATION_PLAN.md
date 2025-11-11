# PR Review Agent - Implementation Plan (MVP)

## Overview

Build a simple PR review agent using Google ADK that analyzes pull requests and posts review comments. This is an MVP focused on getting basic functionality working, with expansion planned for later phases.

## MVP Scope

**What's Included:**
- Fetch PR metadata and diff using GitHub CLI
- Analyze code changes with Gemini LLM
- Post a single summary review comment
- Run as a standalone Python script
- Basic error handling and logging

**What's Deferred (Post-MVP):**
- Docker containerization
- GitHub Actions integration
- Inline/file-specific comments
- Advanced severity classification
- Multi-file batching strategies

## Architecture Design

### Single Agent Approach

**PR Review Agent**
- **Model**: Gemini 2.5 Flash (fast and cost-effective for MVP)
- **Purpose**: Analyze PR changes and provide constructive feedback
- **MVP Capabilities**:
  - Parse PR metadata and diffs
  - Identify obvious code issues and improvements
  - Generate a structured review summary
  - Post review as a single PR comment

### Core Components

#### 1. GitHub Integration (`pr_agent/github_tools.py`)

**MVP GitHub CLI Operations:**
- `gh pr view <number> --json` - Get PR metadata (title, body, author)
- `gh pr diff <number>` - Get code diff
- `gh pr comment <number> --body "..."` - Post summary comment

**Authentication:**
- GitHub Token via `GITHUB_TOKEN` environment variable
- `gh` CLI automatically uses this token
- Required scope: `repo` (for repository access)

**Simple Python Wrapper:**
```python
import subprocess
import json

def get_pr_info(repo: str, pr_number: int) -> dict:
    """Get PR metadata"""
    cmd = ['gh', '-R', repo, 'pr', 'view', str(pr_number),
           '--json', 'title,body,author,headRefName,baseRefName']
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def get_pr_diff(repo: str, pr_number: int) -> str:
    """Get PR diff"""
    cmd = ['gh', '-R', repo, 'pr', 'diff', str(pr_number)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout

def post_pr_comment(repo: str, pr_number: int, body: str) -> None:
    """Post a comment on the PR"""
    cmd = ['gh', '-R', repo, 'pr', 'comment', str(pr_number), '--body', body]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
```

#### 2. Agent Review Logic (`pr_agent/reviewer.py`)

**MVP Analysis Flow:**
1. Get PR metadata (title, description, branches)
2. Get full diff
3. Send to Gemini agent with review instructions
4. Agent analyzes and generates review summary
5. Post summary as PR comment

**Agent Instructions (System Prompt):**
```
You are a code reviewer analyzing a pull request.

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
```

#### 3. Main Execution (`pr_agent/main.py`)

**Simple MVP Flow:**
```python
def main():
    # 1. Load environment variables
    repo = os.getenv('GITHUB_REPOSITORY')  # e.g., "owner/repo"
    pr_number = int(os.getenv('GITHUB_PR_NUMBER'))

    # 2. Fetch PR data
    pr_info = get_pr_info(repo, pr_number)
    pr_diff = get_pr_diff(repo, pr_number)

    # 3. Create review prompt
    prompt = f"""
    Review this pull request:

    Title: {pr_info['title']}
    Description: {pr_info['body']}
    Branch: {pr_info['headRefName']} -> {pr_info['baseRefName']}

    Changes:
    {pr_diff}

    Provide your code review.
    """

    # 4. Get agent review
    agent = create_review_agent()
    response = agent.generate(prompt)
    review_text = response.text

    # 5. Post review comment
    post_pr_comment(repo, pr_number, review_text)

    print(f"Review posted to PR #{pr_number}")
```

**Error Handling:**
- Try/except blocks around GitHub CLI calls
- Log errors to stdout/stderr
- Exit with non-zero code on failure

#### 4. Agent Configuration (`pr_agent/reviewer.py`)

**Create the Review Agent:**
```python
from google.adk.agents import Agent

def create_review_agent() -> Agent:
    """Initialize the PR review agent"""
    return Agent(
        model='gemini-2.5-flash',
        name='pr_reviewer',
        instruction="""You are a code reviewer analyzing a pull request.

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
        Format your response in markdown for GitHub.
        """
    )
```

## MVP Implementation Steps

### Step 1: GitHub CLI Functions (30 min)
**File:** `pr_agent/github_tools.py`

Create three simple functions:
- `get_pr_info(repo, pr_number)` - returns dict with PR metadata
- `get_pr_diff(repo, pr_number)` - returns diff string
- `post_pr_comment(repo, pr_number, body)` - posts comment

Test manually with: `gh pr view 1 --json title,body,author`

### Step 2: Review Agent (20 min)
**File:** `pr_agent/reviewer.py`

Create agent factory:
- `create_review_agent()` - returns configured Agent
- Simple instruction prompt (code quality + security)
- Use Gemini 2.5 Flash model

### Step 3: Main Execution (30 min)
**File:** `pr_agent/main.py`

Implement main flow:
- Load env vars (GITHUB_REPOSITORY, GITHUB_PR_NUMBER)
- Call GitHub functions to get PR data
- Format prompt with PR info + diff
- Get agent response
- Post comment back to PR
- Basic error handling with try/except

### Step 4: Environment Setup (15 min)
**File:** `pr_agent/.env`

Required variables:
```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=europe-west2
GITHUB_TOKEN=ghp_...
GITHUB_REPOSITORY=owner/repo
GITHUB_PR_NUMBER=1
```

### Step 5: Test Locally (15 min)
1. Authenticate: `gcloud auth application-default login`
2. Set GitHub token: `gh auth login` or export GITHUB_TOKEN
3. Run: `python -m pr_agent.main`
4. Check PR for comment

### Step 6: Iterate & Improve
Once basic flow works:
- Refine agent prompt based on actual reviews
- Add better error messages
- Handle edge cases (large diffs, etc.)
- Add logging

## Technical Decisions

### Why Gemini 2.5 Flash?
- Fast response times (< 5 seconds typical)
- Cost-effective ($0.01 per 1M tokens)
- Good code understanding capabilities
- Can upgrade to Pro later if needed

### Why GitHub CLI?
- Simple subprocess calls, no libraries needed
- Built-in authentication via GITHUB_TOKEN
- JSON output easy to parse
- Can test commands manually before coding

### Why Single Comment vs Inline Comments?
- **MVP simplicity**: One comment is easier to implement
- **Better for summary**: Overall review fits single comment format
- **Defer complexity**: Inline comments need commit IDs and line mapping
- **Post-MVP**: Can add inline comments later

## Environment Variables

```bash
# Required - Google Cloud (Vertex AI)
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2

# Required - GitHub
GITHUB_TOKEN=ghp_...
GITHUB_REPOSITORY=owner/repo
GITHUB_PR_NUMBER=123
```

## MVP Success Criteria

**MVP is successful when:**
1. Script runs without errors on a test PR
2. Fetches PR metadata and diff correctly
3. Agent generates a reasonable review (not nonsense)
4. Review comment appears on the PR
5. Takes < 30 seconds for small PR (< 500 lines)

**Good enough for MVP:**
- Review quality doesn't have to be perfect
- Can miss some issues (we'll improve the prompt)
- Basic error messages are fine
- No need for fancy formatting

## Post-MVP Enhancements

**Phase 2 - Robustness:**
- Better error handling and retry logic
- Handle large diffs (split or truncate)
- Improve agent prompt based on results
- Add logging and debugging

**Phase 3 - Features:**
- Inline comments on specific lines
- Severity classification (critical/major/minor)
- File-by-file review for better context
- Configurable review focus areas

**Phase 4 - Deployment:**
- Docker containerization
- GitHub Actions integration
- Support multiple repositories
- CI/CD pipeline
