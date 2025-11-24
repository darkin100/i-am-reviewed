# Environment Variable Validation

This document describes the environment variable validation system implemented in the PR Review Agent.

## Overview

The `ValidateEnvironmentVariables()` function in `pr_agent/main.py` validates all required environment variables before the agent runs. This ensures early detection of configuration issues and provides clear error messages.

## Architecture

The validation system has two layers:

1. **Generic validation** - Validates variables required by all platforms (main.py:89)
2. **Platform-specific validation** - Delegates to each platform implementation via `validate_environment_variables()` method

### Generic Environment Variables

These are validated for all platforms:

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID for Vertex AI |
| `GOOGLE_CLOUD_LOCATION` | Yes | GCP region (e.g., europe-west2) |
| `REPOSITORY` | Optional* | Generic repository identifier |
| `PR_NUMBER` | Optional* | Generic PR/MR number |

*Required if platform-specific equivalents are not provided

### Platform-Specific Variables

Each platform implementation validates its own required variables:

#### GitHub Platform (pr_agent/platforms/github.py:123)

| Variable | Alternative | Purpose |
|----------|-------------|---------|
| `GITHUB_REPOSITORY` | `REPOSITORY` | Repository in format 'owner/repo' |
| `GITHUB_PR_NUMBER` | `PR_NUMBER` | Pull request number |
| `GITHUB_EVENT_PATH` | - | Path to GitHub Actions event file (can extract PR number) |

At least one variable from each row must be present.

#### GitLab Platform (pr_agent/platforms/gitlab.py:196)

| Variable | Alternative | Purpose |
|----------|-------------|---------|
| `CI_PROJECT_PATH` | `REPOSITORY` | Repository in format 'group/project' |
| `CI_MERGE_REQUEST_IID` | `PR_NUMBER` | Merge request IID |
| `GITLAB_TOKEN` | `CI_JOB_TOKEN` | Authentication token (required in CI/CD) |

At least one variable from each row must be present.

## Implementation

### Base Class Method

All platform implementations must implement the abstract method:

```python
def validate_environment_variables(self) -> List[str]:
    """Validate platform-specific environment variables.

    Returns:
        List of missing environment variable names (empty list if all present)
    """
```

### Usage in Main

The validation is called in `main()` after the platform is loaded:

```python
# Get platform implementation
platform = get_platform(args.provider)

# Validate environment variables (generic + platform-specific)
ValidateEnvironmentVariables(platform)
```

## Error Messages

If validation fails, the function:
1. Prints a clear error message listing all missing variables
2. Exits with status code 1

Example error output:

```
Error: Missing required environment variables:
  - GOOGLE_CLOUD_PROJECT
  - REPOSITORY or GITHUB_REPOSITORY
  - PR_NUMBER, GITHUB_PR_NUMBER, or GITHUB_EVENT_PATH

Please set these variables in your .env file or environment.
```

## Adding New Platforms

When adding a new platform, implement the `validate_environment_variables()` method:

1. Check for generic variables (`REPOSITORY`, `PR_NUMBER`)
2. Check for platform-specific alternatives
3. Check for any other platform-required variables
4. Return a list of missing variable names

Example:

```python
def validate_environment_variables(self) -> List[str]:
    missing_vars = []

    # Check repository
    if not os.getenv('REPOSITORY') and not os.getenv('PLATFORM_REPO'):
        missing_vars.append('REPOSITORY or PLATFORM_REPO')

    # Check PR number
    if not os.getenv('PR_NUMBER') and not os.getenv('PLATFORM_PR_ID'):
        missing_vars.append('PR_NUMBER or PLATFORM_PR_ID')

    return missing_vars
```

## Testing

Test the validation with:

```bash
source venv/bin/activate
python -m pytest tests/test_environment_validation.py
```

Or manually:

```python
from pr_agent.main import ValidateEnvironmentVariables
from pr_agent.platforms import get_platform

# Set required variables
os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'europe-west2'
os.environ['REPOSITORY'] = 'owner/repo'
os.environ['PR_NUMBER'] = '123'

# Validate
platform = get_platform('github')
ValidateEnvironmentVariables(platform)  # Should print "✓ Environment variables validated successfully"
```

## See Also

- [DEPLOYMENT.md](DEPLOYMENT.md) - Full list of environment variables used
- [pr_agent/main.py](../pr_agent/main.py) - Main validation function
- [pr_agent/platforms/base.py](../pr_agent/platforms/base.py) - Abstract base class
