#!/bin/bash

# Script to delete and recreate the v1.0 tag
# This will move the v1.0 tag to the current HEAD

set -e  # Exit on any error

TAG_NAME="v1.0"
REMOTE="origin"

echo "========================================"
echo "Retagging ${TAG_NAME}"
echo "========================================"

# Step 1: Delete local tag if it exists
echo ""
echo "[1/4] Checking for local tag ${TAG_NAME}..."
if git tag -l | grep -q "^${TAG_NAME}$"; then
    echo "      Deleting local tag ${TAG_NAME}..."
    git tag -d ${TAG_NAME}
    echo "      ✓ Local tag deleted"
else
    echo "      Local tag ${TAG_NAME} does not exist (skipping)"
fi

# Step 2: Delete remote tag
echo ""
echo "[2/4] Deleting remote tag ${TAG_NAME} from ${REMOTE}..."
if git ls-remote --tags ${REMOTE} | grep -q "refs/tags/${TAG_NAME}$"; then
    git push ${REMOTE} --delete ${TAG_NAME}
    echo "      ✓ Remote tag deleted"
else
    echo "      Remote tag ${TAG_NAME} does not exist on ${REMOTE} (skipping)"
fi

# Step 3: Create new tag at current HEAD
echo ""
echo "[3/4] Creating new tag ${TAG_NAME} at current HEAD..."
git tag ${TAG_NAME}
echo "      ✓ Tag created at $(git rev-parse --short HEAD)"

# Step 4: Push new tag to remote
echo ""
echo "[4/4] Pushing tag ${TAG_NAME} to ${REMOTE}..."
git push ${REMOTE} ${TAG_NAME}
echo "      ✓ Tag pushed to remote"

echo ""
echo "========================================"
echo "✓ Successfully retagged ${TAG_NAME}"
echo "========================================"
