#!/usr/bin/env bash
# tests/test_apc_bundle.sh - Automated tests for scripts/apc-bundle.sh
# Runs without network and requires no API keys.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Ensure temporary test archives are cleaned up on exit
# shellcheck disable=SC2329
cleanup() {
  rm -f apc-bundle-core-*.tar.gz \
        apc-bundle-strat-*.tar.gz \
        apc-bundle-strat-design-*.tar.gz \
        apc-bundle-fix-*.tar.gz \
        apc-bundle-full-*.tar.gz \
        results/test_secret_sample.txt 2>/dev/null || true
}
trap cleanup EXIT INT TERM

pass_count=0
fail_count=0

# --- Test Case 1 ---
echo "Running Case 1: --list for every profile exits 0, and the thesis glob resolves to one path..."
c1_fail=0
for prof in core strat strat-design fix full; do
  if ! ./scripts/apc-bundle.sh --list "$prof" >/dev/null 2>&1; then
    echo "  FAIL: --list $prof exited non-zero" >&2
    c1_fail=1
  fi
done

strat_design_thesis_count=$(./scripts/apc-bundle.sh --list strat-design | grep -c "docs/thesis/" || true)
if [[ $strat_design_thesis_count -ne 1 ]]; then
  echo "  FAIL: thesis glob in strat-design matched $strat_design_thesis_count files (expected 1)" >&2
  c1_fail=1
fi

full_thesis_count=$(./scripts/apc-bundle.sh --list full | grep -c "docs/thesis/" || true)
if [[ $full_thesis_count -ne 1 ]]; then
  echo "  FAIL: thesis glob in full matched $full_thesis_count files (expected 1)" >&2
  c1_fail=1
fi

if [[ $c1_fail -eq 0 ]]; then
  echo "PASS: Case 1 (--list profiles and thesis glob resolution)"
  pass_count=$((pass_count + 1))
else
  echo "FAIL: Case 1 (--list profiles and thesis glob resolution)"
  fail_count=$((fail_count + 1))
fi

# --- Test Case 2 ---
echo "Running Case 2: Real archive from core extracts into empty temp dir and sha256sum -c passes..."
c2_fail=0
tmp_extract="$(mktemp -d)"
archive_out=$(./scripts/apc-bundle.sh core)
archive_file=$(echo "$archive_out" | grep "^Archive: " | awk '{print $2}')

if [[ -z "$archive_file" || ! -f "$archive_file" ]]; then
  echo "  FAIL: Archive '$archive_file' not found" >&2
  c2_fail=1
else
  tar -xzf "$archive_file" -C "$tmp_extract"
  if [[ ! -f "$tmp_extract/MANIFEST.txt" ]]; then
    echo "  FAIL: MANIFEST.txt missing in extracted archive" >&2
    c2_fail=1
  else
    if ! (cd "$tmp_extract" && awk '/^[0-9a-f]{64}/ {print $1 "  " $3}' MANIFEST.txt | sha256sum -c - >/dev/null 2>&1); then
      echo "  FAIL: sha256sum -c verification failed on MANIFEST.txt" >&2
      c2_fail=1
    fi
  fi
  rm -f "$archive_file"
fi
rm -rf "$tmp_extract"

if [[ $c2_fail -eq 0 ]]; then
  echo "PASS: Case 2 (core archive extracts and sha256sum passes)"
  pass_count=$((pass_count + 1))
else
  echo "FAIL: Case 2 (core archive extracts and sha256sum passes)"
  fail_count=$((fail_count + 1))
fi

# --- Test Case 3 ---
echo "Running Case 3: --exclude 'AGENTS.md' removes that file from the archive..."
c3_fail=0
archive_out=$(./scripts/apc-bundle.sh core --exclude 'AGENTS.md')
archive_file=$(echo "$archive_out" | grep "^Archive: " | awk '{print $2}')

if [[ -z "$archive_file" || ! -f "$archive_file" ]]; then
  echo "  FAIL: Archive '$archive_file' not found" >&2
  c3_fail=1
else
  if tar -tzf "$archive_file" | grep -q "^AGENTS.md$"; then
    echo "  FAIL: AGENTS.md unexpectedly present in archive contents" >&2
    c3_fail=1
  fi
  # Verify other core files are present
  if ! tar -tzf "$archive_file" | grep -q "^pyproject.toml$"; then
    echo "  FAIL: pyproject.toml missing from excluded archive" >&2
    c3_fail=1
  fi
  rm -f "$archive_file"
fi

if [[ $c3_fail -eq 0 ]]; then
  echo "PASS: Case 3 (--exclude 'AGENTS.md' removed file)"
  pass_count=$((pass_count + 1))
else
  echo "FAIL: Case 3 (--exclude 'AGENTS.md' removed file)"
  fail_count=$((fail_count + 1))
fi

# --- Test Case 4 ---
echo "Running Case 4: Missing --add path exits 1 and creates no archive..."
c4_fail=0
set +e
missing_out=$(./scripts/apc-bundle.sh core --add nonexistent_file_for_test_123.txt 2>&1)
missing_rc=$?
set -e

if [[ $missing_rc -ne 1 ]]; then
  echo "  FAIL: Expected exit code 1, got $missing_rc" >&2
  c4_fail=1
fi

created_file=$(echo "$missing_out" | grep "^Archive: " | awk '{print $2}' || true)
if [[ -n "$created_file" && -f "$created_file" ]]; then
  rm -f "$created_file"
  echo "  FAIL: Archive was created despite missing --add path" >&2
  c4_fail=1
fi

if [[ $c4_fail -eq 0 ]]; then
  echo "PASS: Case 4 (missing --add path exits 1 without archive)"
  pass_count=$((pass_count + 1))
else
  echo "FAIL: Case 4 (missing --add path exits 1 without archive)"
  fail_count=$((fail_count + 1))
fi

# --- Test Case 5 ---
echo "Running Case 5: --add .env exits 1 and --add results/ file exits 1 (secret guard)..."
c5_fail=0

set +e
env_out=$(./scripts/apc-bundle.sh core --add .env 2>&1)
env_rc=$?
set -e

if [[ $env_rc -ne 1 ]]; then
  echo "  FAIL: --add .env expected exit code 1, got $env_rc" >&2
  c5_fail=1
fi

created_file=$(echo "$env_out" | grep "^Archive: " | awk '{print $2}' || true)
if [[ -n "$created_file" && -f "$created_file" ]]; then
  rm -f "$created_file"
  echo "  FAIL: Archive was created on --add .env" >&2
  c5_fail=1
fi

results_created=0
if [[ ! -d results ]]; then
  mkdir -p results
  results_created=1
fi
touch results/test_secret_sample.txt

set +e
results_out=$(./scripts/apc-bundle.sh core --add results/test_secret_sample.txt 2>&1)
results_rc=$?
set -e

rm -f results/test_secret_sample.txt
if [[ $results_created -eq 1 ]]; then
  rmdir results 2>/dev/null || true
fi

if [[ $results_rc -ne 1 ]]; then
  echo "  FAIL: --add results/... expected exit code 1, got $results_rc" >&2
  c5_fail=1
fi

created_file=$(echo "$results_out" | grep "^Archive: " | awk '{print $2}' || true)
if [[ -n "$created_file" && -f "$created_file" ]]; then
  rm -f "$created_file"
  echo "  FAIL: Archive was created on --add results/..." >&2
  c5_fail=1
fi

if [[ $c5_fail -eq 0 ]]; then
  echo "PASS: Case 5 (secret guard rejected .env and results/ path with exit 1)"
  pass_count=$((pass_count + 1))
else
  echo "FAIL: Case 5 (secret guard rejected .env and results/ path with exit 1)"
  fail_count=$((fail_count + 1))
fi

# --- Test Case 6 ---
echo "Running Case 6: Unknown flag exits 2..."
c6_fail=0
set +e
bad_out=$(./scripts/apc-bundle.sh --badflag-unknown 2>&1)
bad_rc=$?
set -e

if [[ $bad_rc -ne 2 ]]; then
  echo "  FAIL: Expected exit code 2 for unknown flag, got $bad_rc" >&2
  c6_fail=1
fi

created_file=$(echo "$bad_out" | grep "^Archive: " | awk '{print $2}' || true)
if [[ -n "$created_file" && -f "$created_file" ]]; then
  rm -f "$created_file"
  echo "  FAIL: Archive was created on unknown flag" >&2
  c6_fail=1
fi

if [[ $c6_fail -eq 0 ]]; then
  echo "PASS: Case 6 (unknown flag exits 2)"
  pass_count=$((pass_count + 1))
else
  echo "FAIL: Case 6 (unknown flag exits 2)"
  fail_count=$((fail_count + 1))
fi

echo ""
echo "=== Test Results: $pass_count passed, $fail_count failed ==="

if [[ $fail_count -ne 0 ]]; then
  exit 1
fi
exit 0
