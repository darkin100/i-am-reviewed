
## Workload Identity Federation (WIF) - GCP -> GitHub


Create a Workload Identity Pool: Use the gcloud CLI or Terraform to create a pool in GCP. For example, using gcloud:

```bash
gcloud iam workload-identity-pools create "github-identity-pool" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="Github identity pool"
```

Here's what you need to add to your command:

```bash
gcloud iam workload-identity-pools providers create-oidc "github-identity-provider" \
  --location="global" \
  --project="$PROJECT_ID" \
  --workload-identity-pool="github-identity-pool" \
  --display-name="Github identity pool provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.aud=assertion.aud,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner=='YOUR_GITHUB_ORG'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

Replace `YOUR_GITHUB_ORG` with your actual GitHub organization name.

**Key points from the documentation:**

1. The `--attribute-condition` is **required** and must reference claims from the provider
2. For GitHub Actions, the recommended minimum condition is: `assertion.repository_owner=='ORGANIZATION'`
3. You can extend the condition further if needed, for example to restrict to specific branches: `assertion.repository_owner=='ORGANIZATION' && assertion.ref=='refs/heads/main'`

The attribute condition acts as a security filter - it ensures that only tokens from your specified GitHub organization (and optionally specific repos/branches) can authenticate through this workload identity pool.

**Create and Configure a Service Account**: Create a service account in GCP that will be impersonated by GitHub Actions. Grant this service account the necessary IAM roles for your project.

Based on the documentation I reviewed, here's how to set up access for your GitHub Action to publish Docker images to your Artifact Registry repository:

## Step 1: Create a Service Account

First, create a service account that will be used by your GitHub Actions:

```bash
gcloud iam service-accounts create github-actions-sa \
  --project="iamreleased" \
  --display-name="GitHub Actions Service Account"
```

## Step 2: Grant Artifact Registry Permissions

Grant the service account permission to write to your Artifact Registry:

```bash
gcloud artifacts repositories add-iam-policy-binding docker-images \
  --project="iamreleased" \
  --location=europe-west2 \
  --member="serviceAccount:github-actions-sa@iamreleased.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

## Step 3: Grant Workload Identity User Role

Now bind your GitHub identity to the service account. You need to decide how granular you want the access to be:

### Option A: Grant access to a specific repository

```bash
gcloud iam service-accounts add-iam-policy-binding github-actions-sa@iamreleased.iam.gserviceaccount.com \
  --project="iamreleased" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-identity-pool/attribute.repository_owner/YOUR_GITHUB_ORG"
```

### Option B: Grant access to a specific repository and branch (more secure)

```bash
gcloud iam service-accounts add-iam-policy-binding github-actions-sa@iamreleased.iam.gserviceaccount.com \
  --project="iamreleased" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principal://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-identity-pool/subject/repo:YOUR_GITHUB_ORG/YOUR_REPO:ref:refs/heads/main"
```

**To get your PROJECT_NUMBER:**

```bash
gcloud projects describe iamreleased --format="value(projectNumber)"
```

## Step 4: Configure Your GitHub Actions Workflow

Update your GitHub Actions workflow file:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    
    # Required for Workload Identity Federation
    permissions:
      id-token: write
      contents: read
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: 'projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-identity-pool/providers/github-identity-provider'
          service_account: 'github-actions-sa@iamreleased.iam.gserviceaccount.com'
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Configure Docker to use gcloud as credential helper
        run: |
          gcloud auth configure-docker europe-west2-docker.pkg.dev
      
      - name: Build and Push Docker image
        run: |
          docker build -t europe-west2-docker.pkg.dev/iamreleased/docker-images/YOUR_IMAGE_NAME:${{ github.sha }} .
          docker push europe-west2-docker.pkg.dev/iamreleased/docker-images/YOUR_IMAGE_NAME:${{ github.sha }}
```

## Summary

The key concepts here:

1. **Service Account**: Acts as the identity that has permissions to write to Artifact Registry
2. **Workload Identity Binding**: Links your GitHub identity (via the workload identity pool) to the service account
3. **Principal/PrincipalSet**: Defines which GitHub workflows can impersonate the service account
   - Use `principal://` for specific subject (exact repo + branch)
   - Use `principalSet://` with `attribute.repository_owner` for all repos in your GitHub org

Replace:
- `YOUR_GITHUB_ORG` with your GitHub organization name
- `YOUR_REPO` with your repository name (if using Option B)
- `PROJECT_NUMBER` with your actual project number
- `YOUR_IMAGE_NAME` with your desired image name

This setup uses keyless authentication - no service account keys needed!