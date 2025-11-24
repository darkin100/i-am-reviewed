# Deployment Guide

This guide covers deploying the PR Review Agent as a Docker container as part of either a GitHub Action or a Gitlab Job.

## Table of Contents
- [Docker Setup](#docker-setup)
- [GitHub Actions Setup](#github-actions-setup)
- [GitLab Actions Setup](#gitlab-actions-setup)
- [Workload Identity Federation Setup](#workload-identity-federation-setup)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Docker Setup

### Building the Docker Image

```bash
docker build -t pr-review-agent:latest .
```

### Running Locally with Docker

1. **Set up Google Cloud authentication:**
   ```bash
   gcloud auth application-default login
   ```

2. **Authenticate GitHub CLI:**
   ```bash
   gh auth login
   ```

3. **Run the container:**

Whilst you can run the container locally, you need to specify the PR/MR that you want to process
   ```bash
   docker run --rm \
     -e GITHUB_REPOSITORY=owner/repo \
     -e GITHUB_PR_NUMBER=123 \
     -e GOOGLE_CLOUD_PROJECT=your-project-id \
     -e GOOGLE_CLOUD_LOCATION=europe-west2 \
     -v ~/.config/gcloud:/root/.config/gcloud:ro \
     -v ~/.config/gh:/root/.config/gh:ro \
     pr-review-agent:latest
   ```

### Publishing to Container Registry

**Google Container Registry (GCR):**
```bash
# Tag the image
docker tag pr-review-agent:latest gcr.io/YOUR-PROJECT-ID/pr-review-agent:latest

# Push to GCR
docker push gcr.io/YOUR-PROJECT-ID/pr-review-agent:latest
```

**Docker Hub:**
```bash
# Tag the image
docker tag pr-review-agent:latest YOUR-USERNAME/pr-review-agent:latest

# Push to Docker Hub
docker push YOUR-USERNAME/pr-review-agent:latest
```

---

## GitHub Actions Setup

### Prerequisites

1. **Google Cloud Project** with Vertex AI API enabled
2. **Workload Identity Federation** configured (see setup below)
3. **GitHub repository** with appropriate permissions

### Step 1: Configure Workload Identity Federation

See the [Workload Identity Federation Setup](#workload-identity-federation-setup) section below.

### Step 2: Add GitHub Secrets

Navigate to your repository: **Settings > Secrets and variables > Actions**

Add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `WORKLOAD_IDENTITY_PROVIDER` | Full resource name of the Workload Identity Provider | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `SERVICE_ACCOUNT` | Email of the service account | `pr-reviewer@your-project.iam.gserviceaccount.com` |
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID | `my-gcp-project` |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI location | `europe-west2` |

**Note:** `GITHUB_TOKEN` is automatically provided by GitHub Actions and doesn't need to be added as a secret.

### Step 3: Enable the Workflow

The workflow file `.github/workflows/pr-review.yml` is already configured and will trigger automatically on:
- Pull request opened
- Pull request reopened
- Pull request synchronized (new commits pushed)

### Step 4: Test the Action

1. Create a test branch and make some changes
2. Open a pull request
3. The GitHub Action will trigger automatically
4. Check the Actions tab to see the workflow progress
5. The AI review will be posted as a comment on the PR

---

## Workload Identity Federation Setup

Workload Identity Federation allows GitHub Actions to authenticate to Google Cloud without using service account keys (more secure).

### Step 1: Enable Required APIs

```bash
gcloud services enable iamcredentials.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### Step 2: Create a Service Account

```bash
# Create service account
gcloud iam service-accounts create pr-reviewer \
    --display-name="PR Review Agent" \
    --description="Service account for automated PR reviews"

# Get your project ID
PROJECT_ID=$(gcloud config get-value project)

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:pr-reviewer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### Step 3: Create Workload Identity Pool

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Create workload identity pool
gcloud iam workload-identity-pools create github-pool \
    --location="global" \
    --display-name="GitHub Actions Pool"

# Create workload identity provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == 'YOUR-GITHUB-USERNAME'" \
    --issuer-uri="https://token.actions.githubusercontent.com"
```

**Important:** Replace `YOUR-GITHUB-USERNAME` with your GitHub username or organization name.

### Step 4: Grant Service Account Access

```bash
# Allow the GitHub Actions identity to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding \
    pr-reviewer@${PROJECT_ID}.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME"
```

**Important:** Replace `YOUR-GITHUB-USERNAME` and `YOUR-REPO-NAME` with your actual values.

### Step 5: Get the Workload Identity Provider Resource Name

```bash
gcloud iam workload-identity-pools providers describe github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --format="value(name)"
```

This will output something like:
```
projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

Use this value for the `WORKLOAD_IDENTITY_PROVIDER` secret in GitHub.

---

## Testing

### Local Testing with Docker

1. **Build the image:**
   ```bash
   docker build -t pr-review-agent:latest .
   ```

2. **Test on a sample PR:**
   ```bash
   docker run --rm \
     -e GITHUB_REPOSITORY=darkin100/i-am-reviewed \
     -e GITHUB_PR_NUMBER=1 \
     -e GOOGLE_CLOUD_PROJECT=your-project-id \
     -e GOOGLE_CLOUD_LOCATION=europe-west2 \
     -v ~/.config/gcloud:/root/.config/gcloud:ro \
     -v ~/.config/gh:/root/.config/gh:ro \
     pr-review-agent:latest
   ```

### Testing the GitHub Action

1. **Create a test PR:**
   ```bash
   git checkout -b test-pr-review
   echo "# Test" >> TEST.md
   git add TEST.md
   git commit -m "test: trigger PR review"
   git push -u origin test-pr-review
   ```

2. **Open a PR on GitHub** from the `test-pr-review` branch

3. **Monitor the workflow:**
   - Go to the **Actions** tab in your repository
   - Watch the "AI PR Review" workflow run
   - Check for any errors in the logs

4. **Verify the review:**
   - Once complete, the PR should have a new comment with the AI review
   - The comment should include assessment, findings, and positive observations

---

## Troubleshooting

### Common Issues

#### 1. "Error: GITHUB_REPOSITORY environment variable not set"
**Solution:** Ensure the environment variable is properly passed to the Docker container or set in the workflow file.

#### 2. "Error: Workload Identity Federation authentication failed"
**Possible causes:**
- Incorrect `WORKLOAD_IDENTITY_PROVIDER` value
- Service account doesn't have proper permissions
- `attribute-condition` in provider doesn't match your repository

**Solution:**
- Verify the provider resource name
- Check service account IAM bindings
- Review the attribute condition in the Workload Identity Provider

#### 3. "Error: GitHub CLI command failed"
**Possible causes:**
- GitHub token not configured
- Insufficient permissions

**Solution:**
- Verify `GITHUB_TOKEN` is passed correctly
- Check that the workflow has `pull-requests: write` permission

#### 4. "Error: No response from model"
**Possible causes:**
- Vertex AI API not enabled
- Service account lacks `aiplatform.user` role
- Location not supported

**Solution:**
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Grant role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:pr-reviewer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### Debug Mode

To enable verbose logging, modify the Docker run command:

```bash
docker run --rm \
  -e GITHUB_REPOSITORY=... \
  -e GITHUB_PR_NUMBER=... \
  -e GOOGLE_CLOUD_PROJECT=... \
  -e GOOGLE_CLOUD_LOCATION=... \
  -e PYTHONUNBUFFERED=1 \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  -v ~/.config/gh:/root/.config/gh:ro \
  pr-review-agent:latest
```

### Viewing GitHub Actions Logs

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Select the workflow run
4. Click on the "Review PR with AI" job
5. Expand the steps to view detailed logs

---

## Additional Configuration

### Customizing the Review Prompt

Edit `pr_agent/main.py` to customize:
- The review system instruction (lines 70-85)
- The review prompt format (lines 46-60)
- Temperature and other model parameters (lines 87-93)

### Using a Different Model

To use a different Gemini model, edit the `model` parameter in `pr_agent/main.py:88`:

```python
response = client.models.generate_content(
    model='gemini-1.5-pro',  # Change to different model
    contents=prompt,
    ...
)
```

Available models:
- `gemini-2.5-flash` (default, fast and cost-effective)
- `gemini-1.5-pro` (more capable, higher cost)
- `gemini-1.5-flash` (faster, lower cost)

---

## Security Considerations

1. **Never commit service account keys** - Use Workload Identity Federation instead
2. **Use least privilege** - Grant only necessary IAM roles
3. **Restrict repository access** - Use `attribute-condition` in Workload Identity Provider
4. **Rotate credentials** - Periodically review and rotate service accounts
5. **Monitor usage** - Track API calls and review logs for suspicious activity

---

## Cost Optimization

**Vertex AI Pricing:**
- Gemini 2.5 Flash is cost-effective for PR reviews
- Consider setting up budget alerts in GCP
- Monitor token usage in Google Cloud Console

**GitHub Actions:**
- Free for public repositories
- 2,000 minutes/month for private repositories (free tier)
- Consider caching Docker layers to speed up builds

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review GitHub Actions workflow logs
3. Check Google Cloud logs in Cloud Console
4. Open an issue in the repository

## Environment Variables

  | Variable                       | Read/Write | Files                      | Required  | Purpose                           |
  |--------------------------------|------------|----------------------------|-----------|---------------------------------------|
  | GOOGLE_CLOUD_CREDENTIALS_JSON  | Read       | main.py:18                 | Optional  | Service  account JSON for CI/CD        |
  | GOOGLE_APPLICATION_CREDENTIALS | Write      | main.py:32                 | -         | Set by code  (temp file path)          |
  | GOOGLE_CLOUD_PROJECT           | Read       | main.py:185                | Yes       | GCP project ID                          |
  | GOOGLE_CLOUD_LOCATION          | Read       | main.py:186                | Yes       | GCP region                          |
  | REPOSITORY                     | Read       | main.py:51                 | Yes       | Generic repo  identifier               |
  | PR_NUMBER                      | Read       | main.py:73                 | Yes       | Generic PR/MR  number                  |
  | CI_SERVER_HOST                 | Read       | main.py:233, gitlab.py:148 | Optional  | GitLab  hostname (default: gitlab.com) |
  | GITHUB_EVENT_PATH              | Read       | github.py:97               | Optional  | GitHub Actions   event file             |
  | CI_MERGE_REQUEST_IID           | Read       | gitlab.py:124              | Optional  | GitLab MR  number                      |
  | GITLAB_TOKEN                   | Read       | gitlab.py:146              | Yes*      | GitLab PAT  (required for MR API)      |
  | CI_JOB_TOKEN                   | Read       | gitlab.py:147              | Optional  | GitLab CI  token (fallback)            |
  | CI_SERVER_PROTOCOL             | Read       | gitlab.py:149              | Optional  | http/https  (default: https)           |
  | CI_SERVER_URL                  | Read       | gitlab.py:150              | Optional  | Full GitLab  URL                       |
  
Notes:
  - *Required in practice - code expects these but currently doesn't have fallback logic fully
  implemented
  - Yes* GITLAB_TOKEN is required for GitLab because CI_JOB_TOKEN has limited API access