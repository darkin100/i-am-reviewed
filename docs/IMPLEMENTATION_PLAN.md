# PR Review Agent - Implementation Plan

## Overview

Build a PR review agent using Google ADK that can be deployed as a Docker container and integrated into GitHub Actions workflows to automatically review pull requests.

## Architecture Design

### Agent Architecture (Single Agent Approach)

**PR Review Agent (LLM Agent)**
- **Model**: Gemini 2.5 Flash (or Pro for deeper analysis)
- **Purpose**: Analyze code changes and provide constructive review feedback
- **Capabilities**:
  - Parse and understand code diffs
  - Identify code quality issues (bugs, anti-patterns, complexity)
  - Detect potential security vulnerabilities
  - Review documentation and comments
  - Suggest improvements and best practices
  - Prioritize findings (critical, major, minor)

### Core Components

#### 1. GitHub Integration Layer (GitHub CLI)

**Integration Approach:**
We'll use the **GitHub CLI (`gh`)** for GitHub operations. This provides:
- Simple, direct access to GitHub API
- Well-documented command-line interface
- JSON output for easy parsing
- Built-in authentication handling
- No additional services to run

**GitHub CLI Operations:**
- `gh pr view <number>` - Get PR metadata and details
- `gh pr diff <number>` - Get code changes
- `gh pr view <number> --json files` - List changed files
- `gh pr comment <number> --body "..."` - Post PR comment
- `gh pr review <number> --comment --body "..."` - Submit review
- `gh api` - Direct REST API access for advanced operations

**Custom Function Tools:**
The agent will have custom Python functions that wrap `gh` commands:
- `get_pr_info(pr_number)` - Fetch PR metadata
- `get_pr_diff(pr_number)` - Get full diff
- `get_pr_files(pr_number)` - List changed files with stats
- `post_pr_comment(pr_number, body)` - Add general comment
- `post_review_comment(pr_number, path, line, body)` - Add inline review comment

**Authentication:**
- GitHub Token via `GITHUB_TOKEN` environment variable
- `gh` automatically uses this token
- Scopes needed: `repo`, `read:org` (for private repos)
- Alternative: Pre-authenticate with `gh auth login`

#### 2. Review Logic

**Analysis Strategy:**
1. **Fetch PR context**: Get PR title, description, changed files
2. **Analyze each file**: Review diffs for issues
3. **Code quality checks**:
   - Logic errors and bugs
   - Code complexity and maintainability
   - Naming conventions and clarity
   - Error handling patterns
4. **Security review**:
   - Injection vulnerabilities
   - Authentication/authorization issues
   - Sensitive data exposure
   - Dependency vulnerabilities
5. **Best practices**:
   - Design patterns
   - Performance considerations
   - Testing coverage
6. **Generate feedback**: Structure comments with:
   - Severity level
   - File and line number
   - Issue description
   - Suggested fix
   - Reasoning

#### 3. Workflow Orchestration

**Main Flow:**
```
1. Initialize agent with GitHub credentials
2. Parse inputs (repository, PR number from GitHub Action)
3. Fetch PR data
4. For each changed file:
   a. Get diff
   b. Analyze with agent
   c. Generate review comments
5. Batch post comments to GitHub
6. Generate summary comment
7. Exit with status code
```

**Error Handling:**
- Graceful failure if API rate limits hit
- Retry logic for transient failures
- Detailed logging for debugging
- Clear error messages in PR comments if review fails

#### 4. Docker Packaging

**Container Structure:**
```
Dockerfile
├── Base: python:3.11-slim
├── Install GitHub CLI (gh)
├── Install google-adk and Python dependencies
├── Copy pr_agent code
├── Set up entrypoint script
└── Configure environment variables
```

**Dockerfile Example:**
```dockerfile
FROM python:3.11-slim

# Install GitHub CLI
RUN apt-get update && apt-get install -y curl gpg && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
    gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && apt-get install -y gh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY pr_agent/ ./pr_agent/

# Entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
```

**Entry Point:**
- Script that accepts GitHub Action inputs
- Validates environment variables (GITHUB_TOKEN, GITHUB_REPOSITORY, etc.)
- Sets up repository context for gh commands
- Initializes and runs the agent
- Returns appropriate exit codes

## Implementation Phases

### Phase 1: Core Agent Development

1. **GitHub CLI Tools** (`pr_agent/github_tools.py`)
   - Implement custom function tools that wrap `gh` CLI commands
   - `get_pr_info()` - Executes `gh pr view --json` and parses output
   - `get_pr_diff()` - Executes `gh pr diff` and returns diff content
   - `get_pr_files()` - Gets list of changed files with stats
   - `post_pr_comment()` - Posts comments using `gh pr comment`
   - `post_review_comment()` - Posts inline review using `gh pr review`
   - Error handling for CLI failures
   - JSON parsing utilities

2. **PR Review Agent** (`pr_agent/reviewer_agent.py`)
   - Define LlmAgent with Gemini 2.5 Flash
   - Configure with review-specific instructions
   - Register GitHub CLI tools with the agent
   - Define review workflow logic

3. **Orchestration** (`pr_agent/main.py`)
   - Main execution flow
   - Input parsing (from GitHub Action environment)
   - Set repository context for `gh` commands
   - Error handling and logging
   - Review result formatting

### Phase 2: GitHub Action Integration
1. **Action Configuration** (`action.yml`)
   - Define inputs (repo, PR number, token)
   - Define outputs (review status, comment count)
   - Specify Docker image

2. **Entrypoint Script** (`entrypoint.sh`)
   - Parse GitHub Action inputs
   - Set environment variables
   - Execute Python agent
   - Handle exit codes

### Phase 3: Docker Packaging
1. **Dockerfile**
   - Multi-stage build for optimization
   - Include all dependencies
   - Minimal final image

2. **Dependencies** (`requirements.txt`)
   - google-adk
   - python-dotenv
   - GitHub CLI (installed in Dockerfile)
   - Other utilities (logging, etc.)

### Phase 4: Testing & Documentation
1. **Testing**
   - Unit tests for GitHub tools
   - Integration tests with mock GitHub API
   - Test on sample PRs

2. **Documentation**
   - README with usage instructions
   - GitHub Action workflow examples
   - Configuration options

## Technical Decisions

### Why Single Agent vs Multi-Agent?
- PRD specifies "simple PR/MR review agent"
- Single agent reduces complexity and latency
- Can expand to multi-agent later if needed (specialized reviewers)

### Why Gemini 2.5 Flash?
- Fast response times (important for CI/CD)
- Cost-effective for frequent reviews
- Sufficient capability for code review tasks
- Can upgrade to Pro for complex codebases

### GitHub CLI vs Other Integration Methods?

**Chose GitHub CLI because:**
- **Simple and direct**: No additional services or complexity
- **Well-documented**: Extensive documentation and examples
- **JSON output**: Easy to parse and integrate with Python
- **Built-in authentication**: Automatic token handling via `GITHUB_TOKEN`
- **Widely adopted**: Standard tool for GitHub automation
- **Easy testing**: Can manually test `gh` commands before integrating
- **Lower overhead**: No MCP server or API client libraries needed
- **Flexible**: Access to all GitHub features via `gh api`

**Alternatives considered:**
- **MCP Server**: Adds complexity, requires running additional service
- **PyGithub/REST API**: More code to maintain, manual auth handling
- **OpenAPI tools**: 1000+ operations, harder to control and debug

## GitHub CLI Implementation Details

### Custom Function Tools

The agent will use custom function tools that wrap GitHub CLI commands:

```python
import subprocess
import json
import os
from typing import Dict, List, Any

class GitHubCLITools:
    """Wrapper for GitHub CLI commands"""

    def __init__(self, repo: str):
        """
        Initialize with repository context

        Args:
            repo: Repository in format 'owner/name'
        """
        self.repo = repo
        # Verify gh is installed
        self._verify_gh_installed()

    def _verify_gh_installed(self):
        """Check if gh CLI is installed"""
        try:
            subprocess.run(['gh', '--version'],
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("GitHub CLI (gh) is not installed")

    def _run_gh_command(self, args: List[str]) -> str:
        """
        Execute gh command and return output

        Args:
            args: Command arguments (e.g., ['pr', 'view', '123'])

        Returns:
            Command output as string
        """
        cmd = ['gh', '-R', self.repo] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def get_pr_info(self, pr_number: int) -> Dict[str, Any]:
        """
        Get PR metadata

        Args:
            pr_number: Pull request number

        Returns:
            PR information as dict
        """
        output = self._run_gh_command([
            'pr', 'view', str(pr_number),
            '--json', 'title,body,author,files,headRefName,baseRefName'
        ])
        return json.loads(output)

    def get_pr_diff(self, pr_number: int) -> str:
        """
        Get full PR diff

        Args:
            pr_number: Pull request number

        Returns:
            Diff content as string
        """
        return self._run_gh_command(['pr', 'diff', str(pr_number)])

    def get_pr_files(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get list of changed files

        Args:
            pr_number: Pull request number

        Returns:
            List of file changes with stats
        """
        pr_info = self.get_pr_info(pr_number)
        return pr_info.get('files', [])

    def post_pr_comment(self, pr_number: int, body: str) -> None:
        """
        Post a general PR comment

        Args:
            pr_number: Pull request number
            body: Comment text
        """
        self._run_gh_command([
            'pr', 'comment', str(pr_number),
            '--body', body
        ])

    def post_review_comment(self, pr_number: int,
                           path: str, line: int, body: str) -> None:
        """
        Post inline review comment

        Args:
            pr_number: Pull request number
            path: File path
            line: Line number
            body: Comment text
        """
        # Use gh api for inline comments
        # gh pr review doesn't support inline comments directly
        self._run_gh_command([
            'api',
            f'/repos/{self.repo}/pulls/{pr_number}/comments',
            '-f', f'body={body}',
            '-f', f'path={path}',
            '-F', f'line={line}',
            '-f', 'side=RIGHT'
        ])
```

### Agent Configuration

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Initialize GitHub tools
gh_tools = GitHubCLITools(repo=os.getenv('GITHUB_REPOSITORY'))

# Create function tools for the agent
tools = [
    FunctionTool(gh_tools.get_pr_info,
                 description="Get PR metadata including title, description, author, and files"),
    FunctionTool(gh_tools.get_pr_diff,
                 description="Get the full diff of changes in the PR"),
    FunctionTool(gh_tools.get_pr_files,
                 description="Get list of files changed in the PR"),
    FunctionTool(gh_tools.post_pr_comment,
                 description="Post a general comment on the PR"),
]

# Create PR Review Agent
pr_review_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='pr_reviewer',
    instruction='''You are an expert code reviewer. Analyze pull requests for:
    1. Code quality issues (bugs, anti-patterns, complexity)
    2. Security vulnerabilities
    3. Best practices and design patterns
    4. Documentation quality

    Use the available tools to:
    - Get PR information and changed files
    - Analyze the diff for issues
    - Post constructive feedback as comments

    Provide actionable feedback with severity levels.
    Focus on significant issues, not nitpicks.
    ''',
    tools=tools
)
```

## Environment Variables

```bash
# Required - GitHub CLI
GITHUB_TOKEN=<github_token>              # GitHub PAT for gh CLI
GITHUB_REPOSITORY=<owner/repo>           # Target repository (e.g., "microsoft/vscode")
GITHUB_PR_NUMBER=<pr_number>             # PR number to review

# Required - Google Cloud (for Vertex AI)
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=<project_id>
GOOGLE_CLOUD_LOCATION=<region>

# Optional - Review Configuration
REVIEW_SEVERITY=<critical|all>           # Filter review comments (default: all)
MAX_FILES=<number>                       # Limit files to review (default: no limit)
REVIEW_MODE=<comment|review>             # Post as comments or formal review (default: comment)
```

## Success Criteria

1. **Functionality**:
   - Successfully fetches PR data from GitHub
   - Analyzes code changes with LLM
   - Posts structured review comments
   - Works as GitHub Action

2. **Quality**:
   - Identifies genuine code issues (not false positives)
   - Provides actionable feedback
   - Appropriate severity classification
   - Clear and constructive language

3. **Performance**:
   - Reviews typical PR (5-10 files) in < 2 minutes
   - Handles large PRs gracefully (timeout or split)
   - Minimal memory footprint

4. **Reliability**:
   - Handles API errors gracefully
   - Clear error messages
   - Doesn't block PR on failure

## Future Enhancements

- Multi-agent architecture for specialized reviews
- Configurable review rules (rulesets)
- Language-specific analyzers
- Integration with static analysis tools
- Learning from accepted/rejected suggestions
- Support for GitLab, Bitbucket
- Custom review templates per repository
