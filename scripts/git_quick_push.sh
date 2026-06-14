#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: scripts/git_quick_push.sh \"commit message\""
  exit 1
fi

COMMIT_MESSAGE="$1"

cd "$(dirname "$0")/.."

echo
echo "== Repo status before staging =="
git status --short || true

echo
echo "Staging all changes in DroidPuppy..."
git add .

echo
echo "== Repo status after staging =="
git status --short || true

echo
echo "Creating commit..."
git commit -m "$COMMIT_MESSAGE" || {
  echo "Commit did not complete. This can happen if there was nothing new to commit."
  exit 1
}

echo
echo "Pushing to origin/main..."
git push

echo
echo "Done."
