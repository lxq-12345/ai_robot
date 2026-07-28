#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for path in README.md AGENTS.md skills/会话管理协议.md plan mem src config scripts tests resources; do
  if [[ ! -e "$project_root/$path" ]]; then
    echo "Required project path not found: $path" >&2
    exit 1
  fi
done

if ! git -C "$project_root" check-ignore -q docs/.keep; then
  echo "docs/ must remain local-only and ignored by Git" >&2
  exit 1
fi

echo "Workspace layout check passed"
