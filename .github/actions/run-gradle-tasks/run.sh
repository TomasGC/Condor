#!/usr/bin/env bash
# Runs the Gradle tasks named by the JSON array in CONDOR_TASKS, one ./gradlew call per task, in order, stopping
# at the first failure. The list reaches this script through the environment only.
set -euo pipefail

fail() {
  echo "::error::tasks: $1"
  exit 1
}

command -v jq >/dev/null || fail "jq is required on the runner"

# Same rule as the validate-inputs spec, checked again here: a caller that skips the validator still cannot
# reach Gradle with an option, an empty name or a control character (which could forge a workflow command).
jq -e 'type == "array" and length > 0 and all(.[]; type == "string" and length > 0 and (startswith("-") | not)
       and (test("[\u0000-\u001f]") | not))' <<<"${CONDOR_TASKS:-}" >/dev/null 2>&1 \
  || fail "must be a JSON array of task names: not empty, none empty, none starting with '-', no control characters"

mapfile -t -d '' tasks < <(jq -j '.[] + "\u0000"' <<<"$CONDOR_TASKS")

for task in "${tasks[@]}"; do
  echo "::group::./gradlew $task"
  if ! ./gradlew "$task"; then
    echo "::endgroup::"
    fail "./gradlew $task failed"
  fi
  echo "::endgroup::"
done
