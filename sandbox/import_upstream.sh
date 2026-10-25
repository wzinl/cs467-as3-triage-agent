#!/usr/bin/env bash
# Copy the pinned subset of hashicorp/terraform-provider-aws into this repository at the same paths,
# then record the commit and a checksum of every imported file (CI checks them; see AGENTS.md).
# Usage: sandbox/import_upstream.sh [commit]
set -euo pipefail

COMMIT=${1:-1e015f77bf1464d7ca816f19a506ee55d3f92a7f}
# Only what a triage agent reads: issue forms, labelers, the label taxonomy, service names, release notes,
# the triage-related contributor docs and the resource docs. No Go source, no upstream workflows.
PATHS=(
  .github/ISSUE_TEMPLATE .github/labeler-issue-triage.yml .github/labeler-issue-trigger.yml .github/SUPPORT.md
  infrastructure/repository names/data/names_data.hcl names/README.md CHANGELOG.md LICENSE
  docs/issue-reporting-and-lifecycle.md docs/prioritization.md docs/ai-usage.md docs/faq.md
  docs/changelog-process.md docs/naming.md docs/core-services.md docs/running-and-writing-acceptance-tests.md
  website/docs/r website/docs/d
)

root=$(git rev-parse --show-toplevel)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git -C "$tmp" init -q
git -C "$tmp" remote add origin https://github.com/hashicorp/terraform-provider-aws
git -C "$tmp" fetch -q --depth 1 --filter=blob:none origin "$COMMIT"
git -C "$tmp" sparse-checkout set --no-cone "${PATHS[@]/#//}"
git -C "$tmp" checkout -q FETCH_HEAD

for p in "${PATHS[@]}"; do
  [[ -e "$tmp/$p" ]] || { echo "missing upstream path: $p" >&2; exit 1; }
  rm -rf "${root:?}/${p:?}"
  mkdir -p "$root/$(dirname "$p")"
  cp -R "$tmp/$p" "$root/$p"
done
echo "$COMMIT" > "$root/sandbox/upstream-commit.txt"
(cd "$tmp" && find "${PATHS[@]}" -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum) > "$root/sandbox/upstream.sha256"
echo "imported $(wc -l < "$root/sandbox/upstream.sha256") files from $COMMIT"
