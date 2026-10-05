#!/usr/bin/env bash
# Runs the playbook inside a throwaway Ubuntu 24.04 container, twice, to prove it is idempotent.
# Usage (from the repo root): ./ansible/test-in-docker.sh
set -euo pipefail
cd "$(dirname "$0")/.."
docker rm -f ansible-target >/dev/null 2>&1 || true
docker run --rm --name ansible-target -p 5001:5000 -v "$PWD":/project -w /project/ansible \
  -e DEBIAN_FRONTEND=noninteractive -e TZ=Asia/Kolkata ubuntu:24.04 bash -c '
    set -e
    apt-get update -qq && apt-get install -y -qq ansible sudo >/dev/null
    echo "===== RUN 1 (makes changes) ====="
    ansible-playbook playbook.yml
    echo "===== RUN 2 (should report changed=0) ====="
    ansible-playbook playbook.yml | tee /tmp/run2.log
    grep -q "changed=0" /tmp/run2.log && echo "IDEMPOTENT: OK"
    echo "===== Verification ====="
    id notesapp; id devops
    ls -la /opt/notes-service
    cat /opt/notes-service/.env
    curl -s localhost:5000/health; echo
    curl -s localhost:5000/version; echo
  '
