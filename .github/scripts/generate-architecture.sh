#!/usr/bin/env bash
# generate-architecture.sh — Update data-driven sections in ARCHITECTURE.md
# Uses marker-based partial updates to preserve hand-curated content.
# Usage: bash .github/scripts/generate-architecture.sh
# Requires: npx (with gitnexus), jq, awk
# Output: Updates content between <!-- auto:* --> markers in ARCHITECTURE.md
set -euo pipefail

ARCH_FILE="ARCHITECTURE.md"
REPO_NAME="${GITNEXUS_REPO:-}"

# ── Dependency validation ─────────────────────────────────────────────
check_deps() {
  local missing=()
  for cmd in jq npx awk; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "::error::Missing required dependencies: ${missing[*]}" >&2
    exit 1
  fi
}

check_deps

# ── Resolve repo name ────────────────────────────────────────────────
resolve_repo() {
  if [[ -n "$REPO_NAME" ]]; then
    echo "$REPO_NAME"
    return
  fi
  # Check how many repos are indexed; parse "Indexed Repositories (N)" header
  local repo_list
  repo_list=$(npx gitnexus list 2>&1 || true)
  local count
  count=$(echo "$repo_list" | grep -oP 'Indexed Repositories \(\K[0-9]+' 2>/dev/null || echo "1")
  if [[ "$count" -le 1 ]]; then
    # Single repo — no --repo flag needed
    echo ""
  else
    # Multiple repos — use current directory name as repo identifier
    basename "$(pwd)"
  fi
}

REPO=$(resolve_repo)
REPO_FLAG=""
if [[ -n "$REPO" ]]; then
  REPO_FLAG="--repo $REPO"
fi

# ── Validate ARCHITECTURE.md exists with markers ─────────────────────
if [[ ! -f "$ARCH_FILE" ]]; then
  echo "::error::$ARCH_FILE not found. Cannot perform marker-based update." >&2
  exit 1
fi

if ! grep -q '<!-- auto:overview -->' "$ARCH_FILE"; then
  echo "::error::$ARCH_FILE missing <!-- auto:overview --> marker. Add markers before running." >&2
  exit 1
fi

if ! grep -q '<!-- /auto:overview -->' "$ARCH_FILE"; then
  echo "::error::$ARCH_FILE missing <!-- /auto:overview --> closing marker." >&2
  exit 1
fi

# ── Query GitNexus for graph stats ───────────────────────────────────
cypher_query() {
  local query="$1"
  local result
  # shellcheck disable=SC2086
  if ! result=$(npx gitnexus cypher $REPO_FLAG "$query" 2>&1); then
    echo "::warning::Cypher query failed: $result" >&2
    echo ""
    return
  fi
  echo "$result"
}

echo "Querying GitNexus knowledge graph..." >&2

SYMBOL_COUNT=$(cypher_query 'MATCH (n) RETURN count(n) as c' | jq -r '.markdown' | tail -1 | tr -d '| ' || echo "0")
EDGE_COUNT=$(cypher_query 'MATCH ()-[r]->() RETURN count(r) as c' | jq -r '.markdown' | tail -1 | tr -d '| ' || echo "0")
PROCESS_COUNT=$(cypher_query 'MATCH (p:Process) RETURN count(p) as c' | jq -r '.markdown' | tail -1 | tr -d '| ' || echo "0")

# Format numbers with commas
format_number() {
  echo "$1" | sed ':a;s/\B[0-9]\{3\}\>$/,&/;ta'
}

SYMBOL_FMT=$(format_number "$SYMBOL_COUNT")
EDGE_FMT=$(format_number "$EDGE_COUNT")
PROCESS_FMT=$(format_number "$PROCESS_COUNT")

echo "  Symbols: $SYMBOL_FMT, Relationships: $EDGE_FMT, Flows: $PROCESS_FMT" >&2

# ── Count files by extension (with correct exclusions) ───────────────
PY_COUNT=$(find . -name '*.py' \
  -not -path './.git/*' \
  -not -path './.gitnexus/*' \
  -not -path './.venv/*' \
  -not -path './venv/*' \
  -not -path './node_modules/*' \
  | wc -l | tr -d ' ')

RS_COUNT=$(find . -name '*.rs' \
  -not -path './.git/*' \
  -not -path './.gitnexus/*' \
  -not -path './target/*' \
  | wc -l | tr -d ' ')

YML_COUNT=$(find .github/workflows -maxdepth 1 -name '*.yml' 2>/dev/null | wc -l | tr -d ' ')

MD_COUNT=$(find . \( -name '*.md' -o -name '*.rst' \) \
  -not -path './.git/*' \
  -not -path './.gitnexus/*' \
  -not -path './.venv/*' \
  -not -path './venv/*' \
  -not -path './node_modules/*' \
  -not -path './target/*' \
  | wc -l | tr -d ' ')

echo "  Files: py=$PY_COUNT rs=$RS_COUNT yml=$YML_COUNT md=$MD_COUNT" >&2

# ── Build replacement content for overview section ───────────────────
OVERVIEW_CONTENT="| Metric | Count |
|--------|-------|
| Total symbols | ${SYMBOL_FMT} |
| Relationships | ${EDGE_FMT} |
| Execution flows | ${PROCESS_FMT} |
| Python files | ${PY_COUNT} |
| Rust files | ${RS_COUNT} |
| GitHub workflows | ${YML_COUNT} |
| Documentation files | ${MD_COUNT} |"

# ── Replace content between markers ──────────────────────────────────
replace_marker_content() {
  local file="$1"
  local marker="$2"
  local content="$3"
  local start_marker="<!-- auto:${marker} -->"
  local end_marker="<!-- /auto:${marker} -->"

  awk -v start="$start_marker" -v end="$end_marker" -v replacement="$content" '
    $0 == start {
      print
      print replacement
      skip = 1
      next
    }
    $0 == end {
      print
      skip = 0
      next
    }
    !skip { print }
  ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
}

replace_marker_content "$ARCH_FILE" "overview" "$OVERVIEW_CONTENT"

# ── Update timestamp ─────────────────────────────────────────────────
GENERATED_DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
sed -i "s|^> Last updated:.*|> Last updated: ${GENERATED_DATE}|" "$ARCH_FILE"

# ── Validate output ──────────────────────────────────────────────────
LINE_COUNT=$(wc -l < "$ARCH_FILE")
if [[ "$LINE_COUNT" -lt 100 ]]; then
  echo "::error::Generated $ARCH_FILE has only $LINE_COUNT lines (expected >100). Marker replacement may have failed." >&2
  exit 1
fi

if ! head -1 "$ARCH_FILE" | grep -q '^# '; then
  echo "::error::$ARCH_FILE does not start with a heading" >&2
  exit 1
fi

for section in "Codebase Overview" "Architecture Diagram" "Functional Areas" "Key Execution Flows" "Testing Architecture"; do
  if ! grep -q "## $section" "$ARCH_FILE"; then
    echo "::error::$ARCH_FILE missing expected section: $section" >&2
    exit 1
  fi
done

echo "ARCHITECTURE.md updated successfully ($LINE_COUNT lines)" >&2
