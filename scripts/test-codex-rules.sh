#!/usr/bin/env bash
set -euo pipefail

rules=$(cd "$(dirname "${BASH_SOURCE[0]}")/../codex" && pwd -P)/guard.rules
codex_bin=${CODEX_BIN:-$(command -v codex || ls -t "$HOME"/.vscode/extensions/openai.chatgpt-*/bin/*/codex 2>/dev/null | head -1)}
[[ -x "$codex_bin" ]] || { echo 'codex binary not found; set CODEX_BIN' >&2; exit 1; }

expect() {
  local want=$1 got
  shift
  got=$("$codex_bin" execpolicy check --rules "$rules" -- "$@" | jq -r '.decision // "allow"')
  [[ "$got" == "$want" ]] || { echo "codex rules: expected $want, got $got for: $*" >&2; exit 1; }
}

expect allow git status
expect allow git checkout main
expect allow rm -f build.log
expect allow kubectl get pods
expect prompt git push origin main
expect prompt git tag v1.2.0
expect prompt git reset --hard HEAD~1
expect prompt git checkout -- a.ts
expect prompt git checkout .
expect prompt git restore a.ts
expect prompt git clean -fd
expect prompt git stash
expect prompt git branch -D old
expect prompt rm -rf node_modules
expect prompt kubectl apply -f x.yaml
expect prompt helm upgrade api ./chart
expect prompt docker push img
expect prompt gh pr create --fill
expect prompt rm --recursive --force dist
expect prompt rm -r -f dist
expect prompt kubectl drain node1
expect prompt helm delete api
expect prompt k3s crictl rmi --prune
expect prompt crictl rmi abc
expect prompt docker system prune -af
expect prompt terraform destroy
expect allow k3s crictl images
expect allow docker ps
expect forbidden git commit --no-verify -m x
echo 'codex rules: PASS'
