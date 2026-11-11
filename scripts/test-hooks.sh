#!/usr/bin/env bash
set -euo pipefail
PY=${PYTHON:-python3}

hooks=$(cd "$(dirname "${BASH_SOURCE[0]}")/../hooks" && pwd -P)
work=$(mktemp -d /tmp/ai-config-ccg-hooks.XXXXXX)
trap 'gio trash -f "$work" 2>/dev/null || rm -rf "$work"' EXIT

guard() {
  jq -n --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}' |
    "$PY" -I "$hooks/guard-bash.py" | jq -rs '.[0].hookSpecificOutput.permissionDecision // "allow"'
}
expect_guard() {
  local got
  got=$(guard "$2")
  [[ "$got" == "$1" ]] || { echo "guard: expected $1, got $got for: $2" >&2; exit 1; }
}

expect_guard allow 'git status && git diff'
expect_guard allow 'git log --oneline -5'
expect_guard allow 'git stash list'
expect_guard allow 'git tag -l'
expect_guard allow 'git restore --staged file.go'
expect_guard allow 'rm -f build.log'
expect_guard allow 'kubectl get pods'
expect_guard ask 'git push origin main'
expect_guard ask 'cd repo && git -C x push'
expect_guard ask 'git tag v1.2.0'
expect_guard ask 'git reset --hard HEAD~1'
expect_guard ask 'git checkout -- src/a.ts'
expect_guard ask 'git checkout .'
expect_guard ask 'git restore src/a.ts'
expect_guard ask 'git clean -fd'
expect_guard ask 'git stash'
expect_guard ask 'git stash push -m x'
expect_guard ask 'rm -rf node_modules'
expect_guard ask 'kubectl apply -f deploy.yaml'
expect_guard ask 'helm upgrade api ./chart'
expect_guard ask 'gh pr create --fill'
expect_guard ask 'sudo git push'
expect_guard ask 'env GIT_SSH_COMMAND=x git push origin main'
expect_guard ask 'bash -c "git push"'
expect_guard ask 'git  -C repo   push'
expect_guard ask 'rm -fr dist'
expect_guard allow 'git pushd-helper-unrelated'
# flags before the verb
expect_guard ask 'helm -n ingress-nginx upgrade ingress-nginx ./chart -f v.yaml'
expect_guard ask 'kubectl -n hrms-prod rollout restart deploy'
expect_guard ask 'kubectl --context prod delete pvc x'
expect_guard ask 'kubectl --namespace=prod scale sts mongo --replicas=0'
expect_guard ask 'k3s kubectl -n x delete ns ci'
expect_guard ask 'kubectl -n x exec pod -- rm -rf /data'
expect_guard allow 'kubectl -n hrms-prod get pods -o wide'
expect_guard allow 'kubectl --context prod logs deploy/api --tail=50'
expect_guard allow 'kubectl -n x describe pod p'
expect_guard allow 'helm -n x list'
expect_guard allow 'helm -n x get values rel'
# rm flag spellings
expect_guard ask 'rm -r -f /root/backups'
expect_guard ask 'rm -f -r dist'
expect_guard ask 'rm --recursive --force dist'
expect_guard ask 'rm -R -f dist'
expect_guard allow 'rm -f a.log b.log'
# databases and images
expect_guard ask 'mongosh --eval "db.dropDatabase()"'
expect_guard ask 'mongosh --eval "db.users.drop()"'
expect_guard ask 'mongosh --eval "db.users.deleteMany({})"'
expect_guard ask 'mongosh --eval "db.users.updateMany({}, {})"'
expect_guard ask 'psql -c "DROP TABLE users"'
expect_guard ask 'psql -c "truncate table users"'
expect_guard ask 'k3s crictl rmi --prune'
expect_guard ask 'crictl rmi abc'
expect_guard ask 'docker system prune -af'
expect_guard ask 'terraform destroy'
expect_guard allow 'mongosh --eval "db.users.find().limit(1)"'
expect_guard allow 'k3s crictl images'
expect_guard deny 'git commit --no-verify -m x'
expect_guard deny $'git commit -m "x\n\nCo-Authored-By: A <a@b>"'

user_prompt='{"type":"user","message":{"role":"user","content":"fix it"}}'
edit='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{}}]}}'
bash_call='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{}}]}}'
result='{"type":"user","message":{"content":[{"type":"tool_result","content":"ok"}]}}'
say() { jq -nc --arg t "$1" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}'; }

gate() {
  printf '%s\n' "$@" >"$work/t.jsonl"
  jq -n --arg p "$work/t.jsonl" '{transcript_path:$p,stop_hook_active:false}' |
    "$PY" -I "$hooks/proof-gate.py" | jq -rs '.[0].decision // "allow"'
}
expect_gate() {
  local want=$1 got
  shift
  got=$(gate "$@")
  [[ "$got" == "$want" ]] || { echo "gate: expected $want, got $got" >&2; exit 1; }
}

expect_gate allow "$user_prompt" "$(say 'Answer only.')"
expect_gate block "$user_prompt" "$edit" "$result" "$(say 'Done.')"
expect_gate block "$user_prompt" "$bash_call" "$result" "$edit" "$result" "$(say 'Checks: go test passed')"
expect_gate block "$user_prompt" "$edit" "$result" "$bash_call" "$result" "$(say 'Done, looks good.')"
expect_gate allow "$user_prompt" "$edit" "$result" "$bash_call" "$result" "$(say 'Checks: `go test ./...` -> ok')"
expect_gate allow "$user_prompt" "$edit" "$result" "$(say 'Changed X. Not verified: no test runner here.')"
expect_gate allow "$edit" "$result" "$user_prompt" "$(say 'Next answer.')"
printf '%s\n' "$user_prompt" "$edit" >"$work/t.jsonl"
[[ -z "$(jq -n --arg p "$work/t.jsonl" '{transcript_path:$p,stop_hook_active:true}' | "$PY" -I "$hooks/proof-gate.py")" ]]

cx_user='{"type":"event_msg","payload":{"type":"user_message","message":"fix it"}}'
cx_patch='{"type":"event_msg","payload":{"type":"patch_apply_end","success":true}}'
cx_exec='{"type":"response_item","payload":{"type":"custom_tool_call","name":"exec","input":"tools.exec_command({cmd:\"go test ./...\"})"}}'
cx_say() { jq -nc --arg t "$1" '{type:"event_msg",payload:{type:"agent_message",message:$t}}'; }
expect_gate allow "$cx_user" "$(cx_say 'Answer only.')"
expect_gate block "$cx_user" "$cx_patch" "$(cx_say 'Done.')"
expect_gate block "$cx_user" "$cx_exec" "$cx_patch" "$(cx_say 'Checks: go test ok')"
expect_gate allow "$cx_user" "$cx_patch" "$cx_exec" "$(cx_say 'Checks: `go test ./...` -> ok')"
expect_gate allow "$cx_user" "$cx_patch" "$(cx_say 'Not verified: no runner.')"

printf '%s\n' "$user_prompt" "$edit" "$result" "$bash_call" >"$work/t.jsonl"
got=$(jq -n --arg p "$work/t.jsonl" '{transcript_path:$p,stop_hook_active:false,last_assistant_message:"Checks: `make test` -> ok"}' |
  "$PY" -I "$hooks/proof-gate.py" | jq -rs '.[0].decision // "allow"')
[[ "$got" == allow ]] || { echo "gate: last_assistant_message not used" >&2; exit 1; }

"$PY" -I "$hooks/prompt-reminder.py" | jq -e '.hookSpecificOutput.hookEventName == "UserPromptSubmit" and (.hookSpecificOutput.additionalContext | length > 0)' >/dev/null
agy_guard() {
  jq -n --arg c "$1" '{toolCall:{name:"run_command",args:{CommandLine:$c}},transcriptPath:"/x"}' |
    "$PY" -I "$hooks/guard-bash.py" | jq -rs '.[0].decision // "none"'
}
[[ "$(agy_guard 'git push origin main')" == force_ask ]] || { echo 'agy guard: push not asked' >&2; exit 1; }
[[ "$(agy_guard 'git commit --no-verify -m x')" == deny ]] || { echo 'agy guard: no-verify not denied' >&2; exit 1; }
[[ "$(agy_guard 'git status')" == none ]] || { echo 'agy guard: status not passed through' >&2; exit 1; }

"$PY" -I "$hooks/prompt-reminder.py" --antigravity | jq -e '.injectSteps[0].ephemeralMessage | length > 0' >/dev/null

ag_user='{"step_index":"0","type":"USER_INPUT","source":"USER_EXPLICIT","content":"fix it"}'
ag_edit='{"step_index":"1","type":"PLANNER_RESPONSE","tool_calls":[{"name":"edit_file","args":{}}]}'
ag_run='{"step_index":"2","type":"PLANNER_RESPONSE","tool_calls":[{"name":"run_command","args":{"CommandLine":"go test ./..."}}]}'
ag_out='{"step_index":"3","type":"GENERIC","content":"ok"}'
ag_say() { jq -nc --arg t "$1" '{step_index:"9",type:"PLANNER_RESPONSE",content:$t}'; }
ag_gate() {
  printf '%s\n' "$@" >"$work/a.jsonl"
  jq -n --arg p "$work/a.jsonl" '{transcriptPath:$p,executionNum:1,terminationReason:"NO_TOOL_CALL"}' |
    "$PY" -I "$hooks/proof-gate.py" | jq -rs '.[0].decision // "stop"'
}
expect_ag() {
  local want=$1 got
  shift
  got=$(ag_gate "$@")
  [[ "$got" == "$want" ]] || { echo "agy gate: expected $want, got $got" >&2; exit 1; }
}
expect_ag stop "$ag_user" "$(ag_say 'Answer only.')"
expect_ag continue "$ag_user" "$ag_edit" "$ag_out" "$(ag_say 'Done.')"
expect_ag continue "$ag_user" "$ag_run" "$ag_out" "$ag_edit" "$ag_out" "$(ag_say 'Checks: go test ok')"
expect_ag stop "$ag_user" "$ag_edit" "$ag_out" "$ag_run" "$ag_out" "$(ag_say 'Checks: `go test ./...` -> ok')"
expect_ag stop "$ag_user" "$ag_edit" "$ag_out" "$(ag_say 'Not verified: no runner.')"
printf '%s\n' "$ag_user" "$ag_edit" >"$work/a.jsonl"
[[ -z "$(jq -n --arg p "$work/a.jsonl" '{transcriptPath:$p,executionNum:2,terminationReason:"NO_TOOL_CALL"}' | "$PY" -I "$hooks/proof-gate.py")" ]]
[[ -z "$(jq -n --arg p "$work/a.jsonl" '{transcriptPath:$p,executionNum:1,terminationReason:"USER_CANCELED"}' | "$PY" -I "$hooks/proof-gate.py")" ]]
out=$(jq -n '{transcript_path:"/nonexistent/t.jsonl",stop_hook_active:false}' | "$PY" -I "$hooks/proof-gate.py" 2>&1) ||
  { echo "gate: crashed on missing transcript: $out" >&2; exit 1; }
[[ -z "$out" ]]
printf '%s\n' "$user_prompt" 'not json {' "$edit" "$result" "$(say 'Done.')" >"$work/t.jsonl"
[[ "$(jq -n --arg p "$work/t.jsonl" '{transcript_path:$p,stop_hook_active:false}' | "$PY" -I "$hooks/proof-gate.py" | jq -r .decision)" == block ]]
echo 'hooks: PASS'
