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

   **For GitHub:**
   ```bash
   docker run --rm \
     -e REPOSITORY=owner/repo \
     -e PR_NUMBER=123 \
     -e GOOGLE_CLOUD_PROJECT=your-project-id \
     -e GOOGLE_CLOUD_LOCATION=europe-west2 \
     -e GH_TOKEN=your-github-token \
     pr-review-agent:latest
   ```

   **For GitLab:**
   ```bash
   docker run --rm \
     -e REPOSITORY=group/project \
     -e PR_NUMBER=123 \
     -e GOOGLE_CLOUD_PROJECT=your-project-id \
     -e GOOGLE_CLOUD_LOCATION=europe-west2 \
     -e GITLAB_TOKEN=your-gitlab-token \
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
| `GH_TOKEN` | GitHub Personal Access Token (optional if using GITHUB_TOKEN) | `ghp_xxxxxxxxxxxx` |

**Note:** The workflow can use either `secrets.GITHUB_TOKEN` (automatically provided, limited permissions) or `secrets.GH_TOKEN` (personal access token with broader permissions) depending on your needs.

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
     -e REPOSITORY=darkin100/i-am-reviewed \
     -e PR_NUMBER=1 \
     -e GOOGLE_CLOUD_PROJECT=your-project-id \
     -e GOOGLE_CLOUD_LOCATION=europe-west2 \
     -e GH_TOKEN=your-github-token \
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
