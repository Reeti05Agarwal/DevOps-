#!/usr/bin/env bash
# Step 3 demo: deploy v1, rolling update to v2, push a broken release, roll back.
# Usage: CLUSTER=minikube ./scripts/k8s-rollout-demo.sh   (or CLUSTER=kind / CLUSTER=docker-desktop)
# Take a screenshot at each "==>" banner.
set -euo pipefail

CLUSTER="${CLUSTER:-minikube}"
NS=notes
DEPLOY=deployment/notes-service
cd "$(dirname "$0")/.."

banner() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
pause()  { [[ "${NO_PAUSE:-}" == 1 ]] || read -rp "Press Enter to continue..."; }

load_image() {
  case "$CLUSTER" in
    minikube)       minikube image load "$1" ;;
    kind)           kind load docker-image "$1" ;;
    docker-desktop) : ;;  # shares the local Docker image store
    *) echo "Unknown CLUSTER=$CLUSTER" >&2; exit 1 ;;
  esac
}

show() {
  kubectl -n "$NS" get pods -l app=notes-service -o wide
  kubectl -n "$NS" get rs -l app=notes-service
}

banner "Building images 1.0.0 and 2.0.0"
for v in 1.0.0 2.0.0; do
  docker build -q --build-arg APP_VERSION="$v" -t "notes-service:$v" .
  load_image "notes-service:$v"
done

banner "Deploying v1.0.0"
kubectl apply -k k8s/
kubectl -n "$NS" rollout status "$DEPLOY" --timeout=120s
show
kubectl -n "$NS" run curl-v1 --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s http://notes-service/version || true
pause

banner "Rolling update to v2.0.0 (maxSurge=1, maxUnavailable=0)"
kubectl -n "$NS" set image "$DEPLOY" notes-service=notes-service:2.0.0
kubectl -n "$NS" annotate "$DEPLOY" kubernetes.io/change-cause="rolling update to 2.0.0" --overwrite
kubectl -n "$NS" get pods -l app=notes-service -w &
WATCH=$!
kubectl -n "$NS" rollout status "$DEPLOY" --timeout=120s
kill "$WATCH" 2>/dev/null || true
show
kubectl -n "$NS" run curl-v2 --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s http://notes-service/version || true
pause

banner "Pushing a BROKEN release (readiness probe fails)"
kubectl -n "$NS" set env "$DEPLOY" FAIL_READINESS=true
kubectl -n "$NS" annotate "$DEPLOY" kubernetes.io/change-cause="broken release: readiness fails" --overwrite
if ! kubectl -n "$NS" rollout status "$DEPLOY" --timeout=75s; then
  echo "Rollout failed as expected. Old pods kept serving traffic because maxUnavailable=0."
fi
show
pause

banner "Rollout history"
kubectl -n "$NS" rollout history "$DEPLOY"

banner "Rolling back to the last good revision"
kubectl -n "$NS" rollout undo "$DEPLOY"
kubectl -n "$NS" rollout status "$DEPLOY" --timeout=120s
show
kubectl -n "$NS" rollout history "$DEPLOY"
kubectl -n "$NS" run curl-after --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s http://notes-service/version || true

banner "Done. Roll back to an exact revision with: kubectl -n $NS rollout undo $DEPLOY --to-revision=1"
