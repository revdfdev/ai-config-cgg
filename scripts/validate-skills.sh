#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
skill_dir="$root_dir/skills"
required=(plan memory pattern tdd simplify review bug-triage e2e e2e-analysis)

for name in "${required[@]}"; do
  file="$skill_dir/$name/SKILL.md"
  [[ -f "$file" ]] || { echo "missing $file" >&2; exit 1; }
  [[ $(sed -n '1p' "$file") == '---' ]] || { echo "missing front matter: $file" >&2; exit 1; }
  grep -Fqx "name: $name" "$file" || { echo "wrong name: $file" >&2; exit 1; }
  grep -q '^description:' "$file" || { echo "missing description: $file" >&2; exit 1; }
done

for file in templates/playwright/playwright.config.ts; do
  [[ -f "$root_dir/$file" ]] || { echo "missing template: $file" >&2; exit 1; }
done

grep -q "name: 'smoke'" "$root_dir/templates/playwright/playwright.config.ts"
grep -q "name: 'regression'" "$root_dir/templates/playwright/playwright.config.ts"
echo 'skills and templates: PASS'
