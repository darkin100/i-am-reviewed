# Environment Variables

| Variable                       | Read/Write | Files                      | Required  | Purpose                           |
|--------------------------------|------------|----------------------------|-----------|---------------------------------------|
| GOOGLE_APPLICATION_CREDENTIALS | Read       | main.py:32                 | -         | Set by code  (temp file path)          |
| GOOGLE_CLOUD_PROJECT           | Read       | main.py:185                | Yes       | GCP project ID                          |
| GOOGLE_CLOUD_LOCATION          | Read       | main.py:186                | Yes       | GCP region                          |
| REPOSITORY                     | Read       | main.py:51                 | Yes       | Generic repo  identifier               |
| PR_NUMBER                      | Read       | main.py:73                 | Yes       | Generic PR/MR  number  ${{github.event.pull_request.number}} $CI_MERGE_REQUEST_IID                |
| CI_SERVER_HOST                 | Read       | main.py:233, gitlab.py:148 | Optional  | GitLab  hostname (default: gitlab.com) |
| GITLAB_TOKEN                   | Read       | gitlab.py:146              | Yes      | GitLab PAT  (required for MR API)      |
| GH_TOKEN                       | Read       | github.py:119-122          | Yes (GitHub) | GitHub Personal   Access Token for CLI authentication          |
  
  
Notes:
  - *Required in practice - code expects these but currently doesn't have fallback logic fully
  implemented
  - Yes* GITLAB_TOKEN is required for GitLab because CI_JOB_TOKEN has limited API access