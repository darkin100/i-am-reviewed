
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

