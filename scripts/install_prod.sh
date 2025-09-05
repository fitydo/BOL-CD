#!/usr/bin/env bash
set -euo pipefail

# One-command production install for BOL-CD
# Requirements: kubectl, helm
# Env (override as needed):
#   NS             : namespace (default: bolcd)
#   RELEASE        : helm release name (default: bolcd)
#   IMAGE_TAG      : image tag (e.g., sha-<short-sha>)
#   SPLUNK_URL     : Splunk management URL (e.g., https://splunk.example.com:8089)
#   SPLUNK_TOKEN   : Splunk token
#   API_KEYS       : API keys string (default provides viewer/operator/admin demo keys)
#   SLACK_WEBHOOK  : Slack webhook URL (optional)

NS=${NS:-bolcd}
RELEASE=${RELEASE:-bolcd}
IMAGE_TAG=${IMAGE_TAG:-}
SPLUNK_URL=${SPLUNK_URL:-}
SPLUNK_TOKEN=${SPLUNK_TOKEN:-}
API_KEYS=${API_KEYS:-"view:viewer,testop:operator,admin:admin"}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-}

echo "[info] Namespace : ${NS}"
echo "[info] Release   : ${RELEASE}"

kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS"

echo "[step] Creating secrets"
kubectl -n "$NS" apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: bolcd-apikeys
type: Opaque
stringData:
  BOLCD_API_KEYS: ${API_KEYS}
EOF

if [[ -n "${SPLUNK_URL}" && -n "${SPLUNK_TOKEN}" ]]; then
  kubectl -n "$NS" apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: bolcd-secrets
type: Opaque
stringData:
  splunk_url: ${SPLUNK_URL}
  splunk_token: ${SPLUNK_TOKEN}
EOF
else
  echo "[warn] SPLUNK_URL or SPLUNK_TOKEN not provided; ab-daily CronJob will fail until set"
fi

if [[ -n "${SLACK_WEBHOOK}" ]]; then
  kubectl -n "$NS" apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: bolcd-notify
type: Opaque
stringData:
  webhook: ${SLACK_WEBHOOK}
EOF
fi

echo "[step] Preflight"
scripts/k8s-preflight.sh "$NS" --release "$RELEASE" || true

echo "[step] Helm install/upgrade"
EXTRA_SET=""
if [[ -n "${IMAGE_TAG}" ]]; then
  EXTRA_SET="--set image.tag=${IMAGE_TAG}"
fi
helm upgrade --install "$RELEASE" ./deploy/helm -n "$NS" \
  -f deploy/helm/values-prod.yaml ${EXTRA_SET} --create-namespace --wait --timeout 10m

echo "[step] Postflight"
scripts/k8s-preflight.sh "$NS" --release "$RELEASE" --check-post || true

echo "[done] BOL-CD installed. To trigger AB daily once:"
echo "kubectl -n $NS create job --from=cronjob/${RELEASE}-ab-daily ab-manual-\$(date +%s)"


