#!/usr/bin/env bash
# Runs ./gradlew --version (which downloads and unpacks the wrapper's distribution without starting a daemon),
# retrying with exponential backoff and jitter. Both numbers reach this script through the environment only.
set -euo pipefail

fail() {
  echo "::error::$1"
  exit 1
}

# The value is never echoed: it could carry a newline and a forged workflow command.
[[ "${CONDOR_ATTEMPTS:-}" =~ ^[0-9]{1,2}$ ]] && ((10#$CONDOR_ATTEMPTS >= 1 && 10#$CONDOR_ATTEMPTS <= 10)) \
  || fail "attempts: must be an integer from 1 to 10"
[[ "${CONDOR_BACKOFF_SECONDS:-}" =~ ^[0-9]{1,3}$ ]] && ((10#$CONDOR_BACKOFF_SECONDS <= 120)) \
  || fail "backoff-seconds: must be an integer from 0 to 120"
[ -f ./gradlew ] || fail "no ./gradlew in $(pwd)"

attempts=$((10#$CONDOR_ATTEMPTS))
wait=$((10#$CONDOR_BACKOFF_SECONDS))

for ((try = 1; try <= attempts; try++)); do
  ./gradlew --version && exit 0
  ((try < attempts)) || fail "./gradlew --version failed after $attempts attempts"
  pause=$((wait + RANDOM % (wait / 4 + 1)))
  echo "::warning::./gradlew --version failed (attempt $try of $attempts); retrying in ${pause}s"
  sleep "$pause"
  wait=$((wait * 2))
done
