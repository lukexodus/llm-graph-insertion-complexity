#!/usr/bin/env bash
# apc-bundle.sh - Bundle the APC upload set into one self-describing archive.
# Run from the llm-graph-insertion-complexity repo root.

set -euo pipefail

# --- Profiles ---
# Luke can comment out lines inside these arrays as needed.

PROFILE_CORE=(
  AGENTS.md
  docs/context/complete-context.md
  docs/context/data-formats.md
  docs/context/strategy-interface.md
  docs/context/apc-handoff-template.md
  docs/decisions/decision-log.md
  docs/tasks/status.md
  pyproject.toml
)

PROFILE_STRAT=(
  "${PROFILE_CORE[@]}"
  src/graph_insertion/strategies/null.py
  tests/test_strategy_interface.py
  tests/test_null_strategy.py
  docs/rrl/catalogue.md
)

PROFILE_STRAT_DESIGN=(
  "${PROFILE_STRAT[@]}"
  "docs/thesis/*.md"
)

PROFILE_FIX=(
  "${PROFILE_CORE[@]}"
  docs/context/prompt-adapter-contract.md
)

# full: union of all of the above, de-duplicated during resolution
PROFILE_FULL=(
  "${PROFILE_CORE[@]}"
  "${PROFILE_STRAT[@]}"
  "${PROFILE_STRAT_DESIGN[@]}"
  "${PROFILE_FIX[@]}"
)

# Optional reports: all commented out by default; included only with --with-reports
OPTIONAL_REPORTS=(
  # docs/reports/DATA-001-gemini-verify-file-formats.md
  # docs/reports/DATA-002-gemini-mekg-directionality.md
  # docs/reports/DATA-003-gemini-source-text-evidence.md
  # docs/reports/DATA-004-claude-code-name-pool-generator.md
  # docs/reports/DATA-005-gemini-claude-web-backend.md
  # docs/reports/DOC-001-gemini-doc-sync.md
  # docs/reports/FIX-001-gemini-infra-001-followup.md
  # docs/reports/FIX-002-gemini-infra-002-hardening.md
  # docs/reports/FIX-003-gemini-driver-followup.md
  # docs/reports/FIX-004-gemini-harness-pilot-corrections.md
  # docs/reports/FIX-005-claude-code-prompt-v2.md
  # docs/reports/FIX-006-claude-code-observed-model-integrity.md
  # docs/reports/FIX-007-claude-code-pilot-outcome.md
  # docs/reports/FIX-008-claude-code-infra005-hardening.md
  # docs/reports/FIX-009-claude-code-prelive-hardening.md
  # docs/reports/FIX-010-gemini-resume-estimate-unification.md
  # docs/reports/FIX-011-claude-code-command-backend-error-codes.md
  # docs/reports/INFRA-001-claude-code-graph-representation.md
  # docs/reports/INFRA-002-gemini-strategy-interface.md
  # docs/reports/INFRA-003-gemini-corpus-loader.md
  # docs/reports/INFRA-004-gemini-measurement-harness.md
  # docs/reports/INFRA-005-claude-code-null-strategy-e2e.md
  # docs/reports/INFRA-006-gemini-decision-step-llm-client.md
)

show_help() {
  cat << 'EOF'
Usage: scripts/apc-bundle.sh [PROFILE] [OPTIONS]

Profiles:
  core          AGENTS, context docs, decision log, status, pyproject (default)
  strat         core + null strategy, interface tests, catalogue
  strat-design  strat + thesis markdown
  fix           core + prompt adapter contract
  full          union of all profiles, de-duplicated

Options:
  --exclude GLOB    Drop any resolved path matching the glob (repeatable)
  --add PATH        Add an ad hoc file (repeatable)
  --with-reports    Include active entries from OPTIONAL_REPORTS
  --list            Print resolved file list with sizes and exit 0
  --discover        Print files defining core symbols and exit 0
  -h, --help        Show this help message and exit
EOF
}

# Secret guard check
is_secret_or_forbidden() {
  local p="${1#./}"
  local base
  base="$(basename "$p")"
  local lower_p
  lower_p="$(echo "$p" | tr '[:upper:]' '[:lower:]')"

  # Forbidden directories
  case "$p" in
    results|results/*|*/results/*|\
    repositories|repositories/*|*/repositories/*|\
    .git|.git/*|*/.git/*|\
    .venv|.venv/*|*/.venv/*|\
    node_modules|node_modules/*|*/node_modules/*)
      return 0
      ;;
  esac

  # Forbidden filename prefixes/extensions
  case "$base" in
    .env*)
      return 0
      ;;
    *.key|*.pem)
      return 0
      ;;
  esac

  # Forbidden keywords anywhere in path
  case "$lower_p" in
    *secret*|*token*|*credential*)
      return 0
      ;;
  esac

  return 1
}

# --- CLI Parsing ---
PROFILE=""
WITH_REPORTS=0
LIST_ONLY=0
DISCOVER_ONLY=0
EXCLUDES=()
ADDS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    --list)
      LIST_ONLY=1
      shift
      ;;
    --discover)
      DISCOVER_ONLY=1
      shift
      ;;
    --with-reports)
      WITH_REPORTS=1
      shift
      ;;
    --exclude)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --exclude requires a glob argument" >&2
        exit 2
      fi
      EXCLUDES+=("$2")
      shift 2
      ;;
    --add)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --add requires a path argument" >&2
        exit 2
      fi
      ADDS+=("$2")
      shift 2
      ;;
    -*)
      echo "ERROR: Unknown option: $1" >&2
      exit 2
      ;;
    *)
      if [[ -z "$PROFILE" ]]; then
        PROFILE="$1"
        shift
      else
        echo "ERROR: Unexpected argument: $1" >&2
        exit 2
      fi
      ;;
  esac
done

if [[ $DISCOVER_ONLY -eq 1 ]]; then
  grep -rl --include='*.py' -E 'class (Shortlist|MeteredEmbedder|ConceptGraph|FakeEmbedder)|def (embed_text|insert_node|candidate_upper_bound)' src/ 2>/dev/null | sort -u
  exit 0
fi

PROFILE="${PROFILE:-core}"

# Select raw profile items
RAW_PROFILE_ITEMS=()
case "$PROFILE" in
  core)
    RAW_PROFILE_ITEMS=("${PROFILE_CORE[@]}")
    ;;
  strat)
    RAW_PROFILE_ITEMS=("${PROFILE_STRAT[@]}")
    ;;
  strat-design)
    RAW_PROFILE_ITEMS=("${PROFILE_STRAT_DESIGN[@]}")
    ;;
  fix)
    RAW_PROFILE_ITEMS=("${PROFILE_FIX[@]}")
    ;;
  full)
    RAW_PROFILE_ITEMS=("${PROFILE_FULL[@]}")
    ;;
  *)
    echo "ERROR: Unknown profile '$PROFILE'. Valid profiles: core, strat, strat-design, fix, full." >&2
    exit 2
    ;;
esac

# Resolve globs in profile items
RESOLVED_RAW=()
for item in "${RAW_PROFILE_ITEMS[@]}"; do
  if [[ "$item" == "docs/thesis/*.md" ]]; then
    shopt -s nullglob
    matches=(docs/thesis/*.md)
    shopt -u nullglob
    if [[ ${#matches[@]} -ne 1 ]]; then
      echo "ERROR: Thesis glob 'docs/thesis/*.md' must match exactly 1 file, found ${#matches[@]}." >&2
      exit 1
    fi
    RESOLVED_RAW+=("${matches[0]}")
  elif [[ "$item" == *"*"* || "$item" == *"?"* || "$item" == *"["* ]]; then
    shopt -s nullglob
    # shellcheck disable=SC2206
    matches=($item)
    shopt -u nullglob
    if [[ ${#matches[@]} -lt 1 ]]; then
      echo "ERROR: Glob '$item' matched no files." >&2
      exit 1
    fi
    RESOLVED_RAW+=("${matches[@]}")
  else
    RESOLVED_RAW+=("$item")
  fi
done

# Add optional reports if requested
if [[ $WITH_REPORTS -eq 1 ]]; then
  for rep in "${OPTIONAL_REPORTS[@]}"; do
    RESOLVED_RAW+=("$rep")
  done
fi

# Add ad hoc files from --add
for ad in "${ADDS[@]}"; do
  RESOLVED_RAW+=("$ad")
done

# De-duplicate while preserving order
DEDUPED=()
declare -A SEEN=()
for path in "${RESOLVED_RAW[@]}"; do
  norm_path="${path#./}"
  if [[ -z "${SEEN[$norm_path]:-}" ]]; then
    SEEN["$norm_path"]=1
    DEDUPED+=("$norm_path")
  fi
done

# Apply --exclude
FILTERED=()
for path in "${DEDUPED[@]}"; do
  base="$(basename "$path")"
  excluded=0
  for ex in "${EXCLUDES[@]}"; do
    # shellcheck disable=SC2053
    if [[ "$path" == $ex || "$base" == $ex ]]; then
      excluded=1
      break
    fi
  done
  if [[ $excluded -eq 0 ]]; then
    FILTERED+=("$path")
  fi
done

RESOLVED_FILES=("${FILTERED[@]}")

# Validate paths
validation_failed=0
for f in "${RESOLVED_FILES[@]}"; do
  # Secret guard check
  if is_secret_or_forbidden "$f"; then
    echo "ERROR: Path '$f' matches secret guard / forbidden pattern." >&2
    validation_failed=1
    continue
  fi

  # Regular file existence check
  if [[ ! -e "$f" ]]; then
    echo "MISSING: $f" >&2
    validation_failed=1
  elif [[ ! -f "$f" ]]; then
    echo "NOT A REGULAR FILE: $f" >&2
    validation_failed=1
  fi
done

if [[ $validation_failed -ne 0 ]]; then
  exit 1
fi

# Warn if thesis file is over 300 KB
for f in "${RESOLVED_FILES[@]}"; do
  if [[ "$f" == docs/thesis/*.md ]]; then
    thesis_sz=$(wc -c < "$f" | tr -d ' ')
    if [[ $thesis_sz -gt 307200 ]]; then
      echo "WARNING: Thesis file '$f' size is $thesis_sz bytes (> 300 KB)." >&2
    fi
  fi
done

# If --list mode, output files with size and exit 0
if [[ $LIST_ONLY -eq 1 ]]; then
  for f in "${RESOLVED_FILES[@]}"; do
    sz=$(wc -c < "$f" | tr -d ' ')
    printf "%8d  %s\n" "$sz" "$f"
  done
  exit 0
fi

# Packaging
OUT="apc-bundle-${PROFILE}-$(date +%Y%m%d-%H%M).tar.gz"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

# Stage into temp directory preserving repo-relative paths
cp --parents "${RESOLVED_FILES[@]}" "$TMP_DIR/"

# Generate MANIFEST.txt
MANIFEST="$TMP_DIR/MANIFEST.txt"
{
  echo "Profile: $PROFILE"
  echo "Timestamp (UTC): $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
  echo "Git status:"
  git status --porcelain -- "${RESOLVED_FILES[@]}" 2>/dev/null || true
  echo ""
  echo "Paths are repo-relative. Extract with: tar -xzf <archive>."
  echo ""
  echo "Files:"
  for f in "${RESOLVED_FILES[@]}"; do
    sha=$(sha256sum "$f" | awk '{print $1}')
    sz=$(wc -c < "$f" | tr -d ' ')
    echo "$sha  $sz  $f"
  done
} > "$MANIFEST"

# Create archive
tar -czf "$OUT" -C "$TMP_DIR" MANIFEST.txt "${RESOLVED_FILES[@]}"

archive_sz=$(wc -c < "$OUT" | tr -d ' ')
file_cnt=$((${#RESOLVED_FILES[@]} + 1))

echo "Archive: $OUT"
echo "Size: $archive_sz bytes"
echo "File count: $file_cnt (including MANIFEST.txt)"
echo "Contents:"
tar -tzf "$OUT"
