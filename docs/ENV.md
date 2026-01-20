# Environment Variables

| Variable                       | Read/Write | Files                      | Required  | Purpose                           |
|--------------------------------|------------|----------------------------|-----------|---------------------------------------|
| GOOGLE_APPLICATION_CREDENTIALS | Read       | src/config.py                 | -         | Set by code  (temp file path)          |
| GOOGLE_CLOUD_PROJECT           | Read       | src/workflow.py, src/config.py                | Yes       | GCP project ID                          |
| GOOGLE_CLOUD_LOCATION          | Read       | src/config.py                | Yes       | GCP region                          |
| REPOSITORY                     | Read       | src/workflow.py                 | Yes       | Generic repo  identifier               |
| PR_NUMBER                      | Read       | src/workflow.py                 | Yes       | Generic PR/MR  number  ${{github.event.pull_request.number}} $CI_MERGE_REQUEST_IID                |
| CI_SERVER_HOST                 | Read       | src/platforms/gitlab.py | Optional  | GitLab  hostname (default: gitlab.com) |
| GITLAB_TOKEN                   | Read       | src/platforms/gitlab.py              | Yes      | GitLab PAT  (required for MR API)      |
| GH_TOKEN                       | Read       | src/platforms/github.py          | Yes (GitHub) | GitHub Personal   Access Token for CLI authentication          |


Notes:
  - *Required in practice - code expects these but currently doesn't have fallback logic fully
  implemented
  - Yes* GITLAB_TOKEN is required for GitLab because CI_JOB_TOKEN has limited API access
