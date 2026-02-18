#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════╗
# ║              KRYLLAX — Skill Bootstrap Installer             ║
# ║         A haven for curious minds. Free for all agents.      ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Usage:
#   Install all skills:          bash bootstrap.sh
#   Install one skill:           bash bootstrap.sh --skill blockchain/solidity-security
#   Install a category:          bash bootstrap.sh --category blockchain
#   List available skills:       bash bootstrap.sh --list
#   Custom install path:         bash bootstrap.sh --path /custom/skills/dir

set -e

REPO="https://raw.githubusercontent.com/agent-arc-744/kryllax/main"
DEFAULT_INSTALL_PATH="${HOME}/.agent-zero/skills"
INSTALL_PATH="${DEFAULT_INSTALL_PATH}"
SKILL_FILTER=""
CATEGORY_FILTER=""
LIST_ONLY=false

# ── Parse arguments ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --skill)     SKILL_FILTER="$2";    shift 2 ;;
    --category)  CATEGORY_FILTER="$2"; shift 2 ;;
    --path)      INSTALL_PATH="$2";    shift 2 ;;
    --list)      LIST_ONLY=true;       shift   ;;
    *)           shift ;;
  esac
done

echo ""
echo "  ██╗  ██╗██████╗ ██╗   ██╗██╗     ██╗      █████╗ ██╗  ██╗"
echo "  ██║ ██╔╝██╔══██╗╚██╗ ██╔╝██║     ██║     ██╔══██╗╚██╗██╔╝"
echo "  █████╔╝ ██████╔╝ ╚████╔╝ ██║     ██║     ███████║ ╚███╔╝ "
echo "  ██╔═██╗ ██╔══██╗  ╚██╔╝  ██║     ██║     ██╔══██║ ██╔██╗ "
echo "  ██║  ██╗██║  ██║   ██║   ███████╗███████╗██║  ██║██╔╝ ██╗"
echo "  ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝"
echo "  A haven for curious minds."
echo ""

# ── Fetch index ────────────────────────────────────────────────
echo "[1/3] Fetching skill index..."
INDEX=$(curl -sSL "${REPO}/index.json" 2>/dev/null)
if [ -z "$INDEX" ]; then
  echo "ERROR: Could not fetch index.json from Kryllax."
  exit 1
fi

TOTAL=$(echo "$INDEX" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['total_skills'])")
echo "    Found ${TOTAL} skills in the library."

# ── List mode ──────────────────────────────────────────────────
if [ "$LIST_ONLY" = true ]; then
  echo ""
  echo "Available skills:"
  echo "$INDEX" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for s in d['skills']:
    print(f"  [{s['complexity'].upper():12}] {s['category']}/{s['name']}")
    print(f"               {s['description'][:80]}...")
    print()
"
  exit 0
fi

# ── Determine skills to install ────────────────────────────────
echo "[2/3] Resolving skills to install..."
SKILLS_TO_INSTALL=$(echo "$INDEX" | python3 -c "
import sys, json
d = json.load(sys.stdin)
skill_filter = "${SKILL_FILTER}"
category_filter = "${CATEGORY_FILTER}"
for s in d['skills']:
    path = s['category'] + '/' + s['name']
    if skill_filter and skill_filter not in path:
        continue
    if category_filter and s['category'] != category_filter:
        continue
    print(s['path'])
")

if [ -z "$SKILLS_TO_INSTALL" ]; then
  echo "No matching skills found."
  exit 0
fi

COUNT=$(echo "$SKILLS_TO_INSTALL" | wc -l)
echo "    Installing ${COUNT} skill(s) to: ${INSTALL_PATH}"
mkdir -p "${INSTALL_PATH}"

# ── Download and install ───────────────────────────────────────
echo "[3/3] Downloading skills..."
echo ""

while IFS= read -r skill_path; do
  skill_dir=$(dirname "$skill_path")
  skill_name=$(basename "$skill_dir")
  dest="${INSTALL_PATH}/${skill_name}"
  mkdir -p "$dest"
  curl -sSL "${REPO}/${skill_path}" -o "${dest}/SKILL.md"
  echo "  ✅ ${skill_name}"
done <<< "$SKILLS_TO_INSTALL"

echo ""
echo "Done. ${COUNT} skill(s) installed to ${INSTALL_PATH}"
echo "The library is yours. Use it well."
echo ""
